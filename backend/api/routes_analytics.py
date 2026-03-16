from collections import defaultdict
from datetime import UTC, datetime, timedelta
import json
import os
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.agents.hazard_agent import identify_hazards
from backend.agents.risk_matrix_agent import generate_risk_matrix
from backend.agents.safety_score_agent import calculate_safety_score
from backend.core.ai_client import chat_completion
from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.database.models import (
    Company,
    ComplianceCheck,
    Equipment,
    EquipmentInspection,
    HazardTask,
    Incident,
    Project,
    Report,
)

router = APIRouter(tags=["Analytics"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _resolve_analytics_company_id(db: Session) -> int:
    company = db.query(Company).order_by(Company.id.asc()).first()
    if company:
        return company.id

    company = Company(name="Local Demo Company")
    db.add(company)
    db.commit()
    db.refresh(company)
    return company.id


def _bucket_for_severity(severity: int | None) -> str:
    level = severity or 1
    if level <= 1:
        return "low"
    if level == 2:
        return "medium"
    if level == 3:
        return "high"
    return "critical"


def _risk_label_from_score(score: int) -> str:
    if score >= 80:
        return "Low"
    if score >= 60:
        return "Medium"
    return "High"


def _heatmap_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _month_key(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m") if value else None


def _month_labels(months: int) -> list[tuple[str, str]]:
    labels = []
    today = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for offset in range(months - 1, -1, -1):
        month_start = today - timedelta(days=offset * 30)
        labels.append((month_start.strftime("%Y-%m"), month_start.strftime("%b")))
    return labels


def _classify_hazard(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["fall", "height", "scaffold", "ladder"]):
        return "Fall Hazards"
    if any(token in lowered for token in ["ppe", "helmet", "glove", "vest"]):
        return "Missing PPE"
    if any(token in lowered for token in ["electric", "panel", "wire", "shock"]):
        return "Electrical Risk"
    if any(token in lowered for token in ["fire", "extinguisher", "smoke"]):
        return "Fire Risk"
    if any(token in lowered for token in ["forklift", "machine", "equipment", "crane"]):
        return "Equipment Failure"
    return "General Safety"


def _extract_location_from_report(content: str | None) -> str:
    text = (content or "").strip()
    match = re.search(r"location:\s*(.+)", text, re.IGNORECASE)
    if match:
        location = match.group(1).splitlines()[0].strip(" -")
        if location:
            return location.title()
    return "General Area"


def _zone_score(report: Report) -> int:
    severity = report.severity or 1
    likelihood = report.likelihood or 1
    return min(100, severity * 18 + likelihood * 14)


def _build_zone_heatmap_data(reports: list[Report]) -> list[dict]:
    grouped: dict[str, list[Report]] = defaultdict(list)
    for report in reports:
        grouped[_extract_location_from_report(report.content)].append(report)

    zones = []
    for location, items in grouped.items():
        total_score = sum(_zone_score(report) for report in items)
        average_score = round(total_score / len(items))
        top_hazard = _classify_hazard(" ".join((report.content or "") for report in items))
        zones.append(
            {
                "zone": location,
                "reports": len(items),
                "risk_score": average_score,
                "risk_level": _heatmap_level(average_score),
                "top_hazard": top_hazard,
                "summary": f"{len(items)} report(s) flagged {top_hazard.lower()} concerns in {location}.",
                "engine": "rules",
            }
        )

    zones.sort(key=lambda item: item["risk_score"], reverse=True)
    return zones


def _ai_refine_zone_heatmap(zones: list[dict]) -> list[dict] | None:
    if not zones or not os.getenv("OPENAI_API_KEY"):
        return None

    prompt = (
        "You are a workplace safety analyst. Refine the risk summaries for these operational zones. "
        "Return only valid JSON as an array of objects with keys: zone, risk_level, summary. "
        "risk_level must be low, medium, or high. Keep the same zone names.\n\n"
        f"Zones: {json.dumps(zones)}"
    )

    try:
        response = chat_completion(prompt, max_tokens=350)
    except Exception:
        return None

    match = re.search(r"\[.*\]", response, re.DOTALL)
    if not match:
        return None

    try:
        refined = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    mapped = {item.get("zone"): item for item in refined if isinstance(item, dict)}
    updated = []
    for zone in zones:
        refined_zone = mapped.get(zone["zone"], {})
        updated.append(
            {
                **zone,
                "risk_level": refined_zone.get("risk_level", zone["risk_level"]).lower(),
                "summary": str(refined_zone.get("summary", zone["summary"])).strip() or zone["summary"],
                "engine": "ai",
            }
        )
    return updated


def _compliance_rate(db: Session, company_id: int | None) -> int:
    checks = db.query(ComplianceCheck).filter(ComplianceCheck.company_id == company_id).all()
    if not checks:
        return 100
    compliant = sum(1 for check in checks if check.status == "compliant")
    return round((compliant / len(checks)) * 100)


def _inspection_completion_rate(db: Session, company_id: int | None) -> int:
    equipment = db.query(Equipment).filter(Equipment.company_id == company_id).all()
    if not equipment:
        return 100
    current = sum(
        1
        for item in equipment
        if item.last_inspection_date and item.next_inspection_date and item.next_inspection_date >= datetime.now(UTC)
    )
    return round((current / len(equipment)) * 100)


def _safety_score_for_reports(reports: list[Report]) -> int:
    if not reports:
        return 0
    avg_severity = round(sum((report.severity or 1) for report in reports) / len(reports))
    avg_likelihood = round(sum((report.likelihood or 1) for report in reports) / len(reports))
    return calculate_safety_score(avg_severity, avg_likelihood)


def _hazard_categories(project_name: str, project_description: str | None, reports: list[Report]) -> list[dict]:
    detected = identify_hazards(
        "construction",
        {"description": f"{project_name} {project_description or ''} scaffolding ladder electrical ppe"},
    )
    categories = {
        "Fall Hazard": 0,
        "Electrical Risk": 0,
        "Missing PPE": 0,
        "Unsafe Ladder": 0,
    }

    for hazard in detected.get("hazards_detected", []):
        lowered = hazard.lower()
        if "fall" in lowered or "height" in lowered:
            categories["Fall Hazard"] += 1
        elif "elect" in lowered:
            categories["Electrical Risk"] += 1
        elif "ppe" in lowered or "helmet" in lowered:
            categories["Missing PPE"] += 1
        elif "ladder" in lowered:
            categories["Unsafe Ladder"] += 1

    categories["Fall Hazard"] += sum(1 for report in reports if (report.severity or 0) >= 3)
    categories["Electrical Risk"] += sum(1 for report in reports if (report.likelihood or 0) >= 3)
    categories["Missing PPE"] += max(1, len(reports) // 2) if reports else 3
    categories["Unsafe Ladder"] += 1 if "ladder" in (project_description or "").lower() else 1

    return [{"label": key, "count": value} for key, value in categories.items()]


def _recent_activity(project_name: str, reports: list[Report]) -> list[str]:
    activity = []

    for report in sorted(reports, key=lambda item: item.created_at or datetime.min, reverse=True)[:4]:
        if report.created_at:
            activity.append(f"Risk report generated for {project_name} on {report.created_at.strftime('%d %b %Y')}")

    if not activity:
        activity = [
            f"Risk report generated for {project_name}",
            f"Hazard detected in {project_name}",
            "New inspection uploaded",
            "Compliance check completed",
        ]

    return activity


@router.get("/dashboard/metrics")
async def dashboard_metrics(
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    results = (
        db.query(Report.severity, func.count(Report.id))
        .filter(Report.company_id == user.company_id)
        .group_by(Report.severity)
        .all()
    )
    metrics = {severity: count for severity, count in results}
    return {"metrics": metrics}


@router.get("/analytics/safety-summary")
async def analytics_safety_summary(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    reports = db.query(Report).filter(Report.company_id == company_id, Report.created_at >= cutoff).all()
    incidents = db.query(Incident).filter(Incident.company_id == company_id, Incident.created_at >= cutoff).all()
    tasks = db.query(HazardTask).filter(HazardTask.company_id == company_id).all()
    open_tasks = sum(1 for task in tasks if str(getattr(task.status, "value", task.status)) in {"open", "in_progress"})
    projects = db.query(Project).filter(Project.company_id == company_id).all()

    site_rollup = []
    for project in projects:
        project_reports = [report for report in reports if report.project_id == project.id]
        project_incidents = [incident for incident in incidents if incident.project_id == project.id]
        if project_reports or project_incidents:
            site_rollup.append(
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "hazards": len(project_reports),
                    "incidents": len(project_incidents),
                }
            )

    site_rollup.sort(key=lambda item: (item["hazards"] + item["incidents"]), reverse=True)

    return {
        "period_days": days,
        "hazards_detected": len(reports),
        "high_risk_hazards": sum(1 for report in reports if (report.severity or 0) >= 3),
        "incidents_reported": len(incidents),
        "average_safety_score": _safety_score_for_reports(reports),
        "open_tasks": open_tasks,
        "inspection_completion_rate": _inspection_completion_rate(db, company_id),
        "compliance_rate": _compliance_rate(db, company_id),
        "active_sites": len(projects),
        "top_sites": site_rollup[:5],
    }


@router.get("/analytics/risk-trends")
async def analytics_risk_trends(
    months: int = Query(6, ge=3, le=12),
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    reports = db.query(Report).filter(Report.company_id == company_id).all()
    incidents = db.query(Incident).filter(Incident.company_id == company_id).all()
    equipment_inspections = db.query(EquipmentInspection).filter(EquipmentInspection.company_id == company_id).all()
    tasks = db.query(HazardTask).filter(HazardTask.company_id == company_id).all()

    buckets = _month_labels(months)
    labels = [label for _, label in buckets]
    hazard_counts = []
    incident_counts = []
    safety_scores = []
    inspection_counts = []
    open_task_counts = []

    for month_key, _display in buckets:
        month_reports = [item for item in reports if _month_key(item.created_at) == month_key]
        month_incidents = [item for item in incidents if _month_key(item.created_at) == month_key]
        month_inspections = [item for item in equipment_inspections if _month_key(item.inspection_date) == month_key]
        month_open_tasks = [
            item
            for item in tasks
            if _month_key(item.created_at) == month_key and str(getattr(item.status, "value", item.status)) in {"open", "in_progress"}
        ]

        hazard_counts.append(len(month_reports))
        incident_counts.append(len(month_incidents))
        safety_scores.append(_safety_score_for_reports(month_reports))
        inspection_counts.append(len(month_inspections))
        open_task_counts.append(len(month_open_tasks))

    return {
        "labels": labels,
        "hazards": hazard_counts,
        "incidents": incident_counts,
        "safety_scores": safety_scores,
        "inspections": inspection_counts,
        "open_tasks": open_task_counts,
    }


@router.get("/analytics/hazard-types")
async def analytics_hazard_types(
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    counter: dict[str, int] = defaultdict(int)

    for report in db.query(Report).filter(Report.company_id == company_id).all():
        counter[_classify_hazard(report.content or "general hazard")] += 1
    for incident in db.query(Incident).filter(Incident.company_id == company_id).all():
        counter[_classify_hazard(f"{incident.incident_type} {incident.description}")] += 1
    for task in db.query(HazardTask).filter(HazardTask.company_id == company_id).all():
        counter[_classify_hazard(f"{task.hazard_type or ''} {task.title} {task.description or ''}")] += 1
    for inspection in db.query(EquipmentInspection).filter(EquipmentInspection.company_id == company_id).all():
        counter[_classify_hazard(f"{inspection.issues_found or ''} {inspection.checklist_summary or ''}")] += 1

    items = sorted(counter.items(), key=lambda item: item[1], reverse=True)
    return {"items": [{"label": label, "count": count} for label, count in items[:6]]}


@router.get("/analytics/risk-distribution")
async def analytics_risk_distribution(
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    reports = db.query(Report).filter(Report.company_id == company_id).all()
    for report in reports:
        distribution[_bucket_for_severity(report.severity)] += 1
    return distribution


@router.get("/analytics/risk-matrix")
async def analytics_risk_matrix(
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    matrix = {
        "low": {"low": 0, "medium": 0, "high": 0},
        "medium": {"low": 0, "medium": 0, "high": 0},
        "high": {"low": 0, "medium": 0, "high": 0},
    }

    def bucket(value: int | None) -> str:
        score = value or 1
        if score <= 1:
            return "low"
        if score == 2:
            return "medium"
        return "high"

    for report in db.query(Report).filter(Report.company_id == company_id).all():
        severity_bucket = bucket(report.severity)
        likelihood_bucket = bucket(report.likelihood)
        matrix[likelihood_bucket][severity_bucket] += 1

    return matrix


@router.get("/dashboard/executive-summary/{project_id}")
async def dashboard_executive_summary(
    project_id: int,
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.company_id == company_id)
        .first()
    )

    if project:
        reports = (
            db.query(Report)
            .filter(Report.project_id == project_id, Report.company_id == company_id)
            .all()
        )
    else:
        reports = db.query(Report).filter(Report.company_id == company_id).all()

    project_name = project.name if project else "Local Demo Safety Dashboard"
    project_description = project.description if project else "Generated from saved incident and hazard reports"
    active_projects = db.query(Project).filter(Project.company_id == company_id).count() or 1

    if reports:
        avg_severity = round(sum((report.severity or 1) for report in reports) / len(reports))
        avg_likelihood = round(sum((report.likelihood or 1) for report in reports) / len(reports))
        hazards = len(reports)
        critical = sum(1 for report in reports if (report.severity or 0) >= 4)
    else:
        avg_severity = 2
        avg_likelihood = 2
        hazards = 0
        critical = 0

    score = calculate_safety_score(avg_severity, avg_likelihood)
    risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}

    if reports:
        for report in reports:
            risk_distribution[_bucket_for_severity(report.severity)] += 1

    hazard_categories = _hazard_categories(project_name, project_description, reports)
    recommendations = max(critical + 2, 1) if reports else 0

    return {
        "project": project_name,
        "score": score,
        "risk_level": _risk_label_from_score(score),
        "hazards": hazards,
        "critical": critical,
        "recommendations": recommendations,
        "total_reports": len(reports),
        "active_projects": active_projects,
        "risk_distribution": risk_distribution,
        "hazard_categories": hazard_categories,
        "recent_activity": _recent_activity(project_name, reports),
    }


@router.post("/risk-heatmap")
def risk_heatmap(
    severity: int,
    likelihood: int,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    matrix = generate_risk_matrix(severity, likelihood)
    return {"severity": severity, "likelihood": likelihood, "risk_level": matrix}


@router.get("/analytics/zone-heatmap")
async def analytics_zone_heatmap(
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    reports = (
        db.query(Report)
        .filter(Report.company_id == company_id)
        .order_by(Report.created_at.desc())
        .all()
    )

    zones = _build_zone_heatmap_data(reports)
    ai_zones = _ai_refine_zone_heatmap(zones)

    return {
        "zones": ai_zones or zones,
        "engine": "ai" if ai_zones else "rules",
        "updated_from_reports": True,
        "report_count": len(reports),
    }
