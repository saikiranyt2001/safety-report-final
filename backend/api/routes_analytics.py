from collections import defaultdict
import csv
from datetime import UTC, datetime, timedelta
from io import BytesIO, StringIO
import json
import os
import re

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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


def _series_value(series: list, idx: int) -> int:
    return series[idx] if idx < len(series) else 0


def _build_kpi_export_rows(
    summary: dict,
    trends: dict,
    distribution: dict,
    project_name: str,
    days: int,
    months: int,
) -> list[list]:
    rows: list[list] = []
    rows.append(["KPI Dashboard Export"])
    rows.append(["Generated At (UTC)", datetime.now(UTC).isoformat()])
    rows.append(["Site", project_name])
    rows.append(["Period Days", days])
    rows.append(["Trend Months", months])
    rows.append([])

    rows.append(["Summary KPI", "Value"])
    rows.append(["Compliance Rate", summary.get("compliance_rate", 0)])
    rows.append(["Open Actions", summary.get("open_tasks", 0)])
    rows.append(["Critical Alerts", summary.get("high_risk_hazards", 0)])
    rows.append(["Inspection Completion", summary.get("inspection_completion_rate", 0)])
    rows.append(["Hazards Detected", summary.get("hazards_detected", 0)])
    rows.append(["Incidents Reported", summary.get("incidents_reported", 0)])
    rows.append([])

    rows.append(["Risk Distribution", "Count"])
    rows.append(["Low", distribution.get("low", 0)])
    rows.append(["Medium", distribution.get("medium", 0)])
    rows.append(["High", distribution.get("high", 0)])
    rows.append(["Critical", distribution.get("critical", 0)])
    rows.append([])

    rows.append(["Trend Label", "Hazards", "Incidents", "Safety Score", "Inspections", "Open Tasks"])
    labels = trends.get("labels", [])
    hazards = trends.get("hazards", [])
    incidents = trends.get("incidents", [])
    safety_scores = trends.get("safety_scores", [])
    inspections = trends.get("inspections", [])
    open_tasks = trends.get("open_tasks", [])

    for idx, label in enumerate(labels):
        rows.append([
            label,
            _series_value(hazards, idx),
            _series_value(incidents, idx),
            _series_value(safety_scores, idx),
            _series_value(inspections, idx),
            _series_value(open_tasks, idx),
        ])

    return rows


def _draw_kpi_pdf_card(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    value: str,
) -> None:
    pdf.setFillColor(colors.HexColor("#f8fbff"))
    pdf.roundRect(x, y - h, w, h, 8, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#d9e6f5"))
    pdf.roundRect(x, y - h, w, h, 8, fill=0, stroke=1)
    pdf.setFillColor(colors.HexColor("#3c4a57"))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x + 8, y - 14, title)
    pdf.setFillColor(colors.HexColor("#102a43"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x + 8, y - 34, value)


def _render_kpi_export_pdf(
    summary: dict,
    trends: dict,
    distribution: dict,
    project_name: str,
    days: int,
    months: int,
) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    pdf.setFillColor(colors.HexColor("#0b63ce"))
    pdf.rect(0, height - 92, width, 92, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(36, height - 42, "KPI Dashboard Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(36, height - 62, f"Site: {project_name}")
    pdf.drawString(200, height - 62, f"Days: {days}")
    pdf.drawString(280, height - 62, f"Months: {months}")
    pdf.drawString(370, height - 62, f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")

    # Summary cards
    top_y = height - 112
    card_w = (width - 90) / 4
    cards = [
        ("Compliance Rate", f"{summary.get('compliance_rate', 0)}%"),
        ("Open Actions", str(summary.get("open_tasks", 0))),
        ("Critical Alerts", str(summary.get("high_risk_hazards", 0))),
        ("Inspection Completion", f"{summary.get('inspection_completion_rate', 0)}%"),
    ]
    for idx, (title, value) in enumerate(cards):
        _draw_kpi_pdf_card(pdf, 36 + (idx * (card_w + 6)), top_y, card_w, 46, title, value)

    # Risk distribution section
    section_y = top_y - 64
    pdf.setFillColor(colors.HexColor("#102a43"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(36, section_y, "Risk Distribution")
    dist = [
        ("Low", distribution.get("low", 0), "#2f9e44"),
        ("Medium", distribution.get("medium", 0), "#f29900"),
        ("High", distribution.get("high", 0), "#e8590c"),
        ("Critical", distribution.get("critical", 0), "#c92a2a"),
    ]
    block_y = section_y - 14
    block_w = (width - 90) / 4
    for idx, (label, value, color_hex) in enumerate(dist):
        x = 36 + (idx * (block_w + 6))
        pdf.setFillColor(colors.HexColor(color_hex))
        pdf.roundRect(x, block_y - 30, block_w, 30, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(x + 8, block_y - 12, label)
        pdf.drawRightString(x + block_w - 8, block_y - 12, str(value))

    # Trend table
    table_y = block_y - 48
    headers = ["Label", "Hazards", "Incidents", "Score", "Inspections", "Open Tasks"]
    col_widths = [120, 70, 70, 70, 90, 100]
    x = 36

    pdf.setFillColor(colors.HexColor("#e9f2ff"))
    pdf.rect(x, table_y - 16, sum(col_widths), 16, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#102a43"))
    pdf.setFont("Helvetica-Bold", 9)
    offset = x
    for i, header in enumerate(headers):
        pdf.drawString(offset + 4, table_y - 11, header)
        offset += col_widths[i]

    labels = trends.get("labels", [])
    hazards = trends.get("hazards", [])
    incidents = trends.get("incidents", [])
    safety_scores = trends.get("safety_scores", [])
    inspections = trends.get("inspections", [])
    open_tasks = trends.get("open_tasks", [])

    row_y = table_y - 20
    pdf.setFont("Helvetica", 8)
    for idx, label in enumerate(labels):
        if row_y < 46:
            pdf.showPage()
            row_y = height - 50
            pdf.setFont("Helvetica", 8)

        if idx % 2 == 0:
            pdf.setFillColor(colors.HexColor("#f7fbff"))
            pdf.rect(x, row_y - 12, sum(col_widths), 12, fill=1, stroke=0)

        values = [
            str(label),
            str(_series_value(hazards, idx)),
            str(_series_value(incidents, idx)),
            str(_series_value(safety_scores, idx)),
            str(_series_value(inspections, idx)),
            str(_series_value(open_tasks, idx)),
        ]
        offset = x
        pdf.setFillColor(colors.HexColor("#1f2937"))
        for col_idx, value in enumerate(values):
            pdf.drawString(offset + 4, row_y - 9, value[:20])
            offset += col_widths[col_idx]
        row_y -= 12

    pdf.save()
    buffer.seek(0)
    return buffer


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
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    report_query = db.query(Report).filter(Report.company_id == company_id, Report.created_at >= cutoff)
    incident_query = db.query(Incident).filter(Incident.company_id == company_id, Incident.created_at >= cutoff)
    tasks_query = db.query(HazardTask).filter(HazardTask.company_id == company_id)

    if project_id is not None:
        report_query = report_query.filter(Report.project_id == project_id)
        incident_query = incident_query.filter(Incident.project_id == project_id)
        tasks_query = tasks_query.filter(HazardTask.project_id == project_id)

    reports = report_query.all()
    incidents = incident_query.all()
    tasks = tasks_query.all()
    open_tasks = sum(1 for task in tasks if str(getattr(task.status, "value", task.status)) in {"open", "in_progress"})
    project_query = db.query(Project).filter(Project.company_id == company_id)
    if project_id is not None:
        project_query = project_query.filter(Project.id == project_id)
    projects = project_query.all()

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
        "project_id": project_id,
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
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    report_query = db.query(Report).filter(Report.company_id == company_id)
    incident_query = db.query(Incident).filter(Incident.company_id == company_id)
    tasks_query = db.query(HazardTask).filter(HazardTask.company_id == company_id)

    if project_id is not None:
        report_query = report_query.filter(Report.project_id == project_id)
        incident_query = incident_query.filter(Incident.project_id == project_id)
        tasks_query = tasks_query.filter(HazardTask.project_id == project_id)

    reports = report_query.all()
    incidents = incident_query.all()
    equipment_inspections = db.query(EquipmentInspection).filter(EquipmentInspection.company_id == company_id).all()
    tasks = tasks_query.all()

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
        "project_id": project_id,
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
    project_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    company_id = _resolve_analytics_company_id(db)
    distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    report_query = db.query(Report).filter(Report.company_id == company_id)
    if project_id is not None:
        report_query = report_query.filter(Report.project_id == project_id)
    reports = report_query.all()
    for report in reports:
        distribution[_bucket_for_severity(report.severity)] += 1
    return {
        **distribution,
        "project_id": project_id,
    }


@router.get("/analytics/kpi-export")
async def analytics_kpi_export(
    days: int = Query(30, ge=7, le=365),
    months: int = Query(6, ge=3, le=12),
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    project_id: int | None = Query(None, ge=1),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    summary = await analytics_safety_summary(days=days, project_id=project_id, db=db)
    trends = await analytics_risk_trends(months=months, project_id=project_id, db=db)
    distribution = await analytics_risk_distribution(project_id=project_id, db=db)

    project_name = "All Sites"
    if project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.company_id == user.company_id)
            .first()
        )
        if project:
            project_name = project.name

    rows = _build_kpi_export_rows(summary, trends, distribution, project_name, days, months)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if format == "pdf":
        pdf_buffer = _render_kpi_export_pdf(summary, trends, distribution, project_name, days, months)
        filename = f"kpi_dashboard_{timestamp}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    for row in rows:
        writer.writerow(row)

    filename = f"kpi_dashboard_{timestamp}.csv"
    content = csv_buffer.getvalue()
    csv_buffer.close()

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
