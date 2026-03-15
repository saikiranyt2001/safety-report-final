import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Project, Report
from backend.agents.safety_score_agent import calculate_safety_score
from backend.core.rbac import require_roles
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_report_generated
from backend.tasks.report_task import generate_report_task

router = APIRouter(tags=["Reports"])

STORAGE_DIR = "storage/reports"
os.makedirs(STORAGE_DIR, exist_ok=True)


class ReportCreatePayload(BaseModel):
    report_id: str | None = None
    project_id: int | None = None
    date: str | None = None
    time: str | None = None
    location: str | None = None
    department: str | None = None
    employee_name: str | None = None
    employee_id: str | None = None
    role: str | None = None
    hazard_type: str | None = None
    risk_level: str | None = None
    description: str | None = None
    risk_score: int | None = None
    severity: str | None = None
    probability: str | None = None
    root_cause: str | None = None
    immediate_action: str | None = None
    preventive_action: str | None = None
    responsible_person: str | None = None
    deadline: str | None = None
    status: str | None = None
    evidence_url: str | None = None


# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _risk_level_from_score(score: int) -> str:
    if score >= 80:
        return "Low"
    if score >= 60:
        return "Medium"
    return "High"


def _severity_score_from_risk_level(risk_level: str | None) -> int:
    mapping = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return mapping.get((risk_level or "").strip().lower(), 2)


def _risk_level_from_severity(severity: int | None) -> str:
    mapping = {
        1: "Low",
        2: "Medium",
        3: "High",
        4: "Critical",
    }
    return mapping.get(severity or 2, "Medium")


# Generate Report
@router.post("/generate-report")
async def generate_report(
    project_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.company_id == user.company_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    hazards = "Slip hazard near machine"
    risk_score = "High"

    task = generate_report_task.delay(project_id, hazards, risk_score)

    log_activity(
        db,
        user.user_id,
        "Generated safety report",
        event_type="user",
        details=f"Started report generation for project {project_id} with task {task.id}",
        company_id=user.company_id,
    )

    notify_report_generated(
        db,
        company_id=user.company_id,
        project=project.name,
        task_id=str(task.id),
    )

    return {
        "message": "Report generation started",
        "task_id": task.id
    }


@router.post("/reports", status_code=201)
async def create_report_record(
    payload: ReportCreatePayload,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    content_parts = [
        payload.description,
        f"Location: {payload.location}" if payload.location else None,
        f"Department: {payload.department}" if payload.department else None,
        f"Hazard: {payload.hazard_type}" if payload.hazard_type else None,
        f"Immediate action: {payload.immediate_action}" if payload.immediate_action else None,
        f"Preventive action: {payload.preventive_action}" if payload.preventive_action else None,
        f"Evidence: {payload.evidence_url}" if payload.evidence_url else None,
    ]
    report = Report(
        company_id=user.company_id,
        project_id=payload.project_id,
        content="\n".join(part for part in content_parts if part),
        severity=_severity_score_from_risk_level(payload.risk_level),
        likelihood=_severity_score_from_risk_level(payload.risk_level),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    log_activity(
        db,
        user.user_id,
        "Created incident report record",
        event_type="user",
        details=f"Created report {report.id} from frontend incident form",
        company_id=user.company_id,
    )

    return {
        "id": report.id,
        "message": "Report saved",
    }


@router.get("/reports")
def list_reports(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Report)
        .filter(Report.company_id == user.company_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "project_id": row.project_id,
            "content": row.content or "",
            "severity": row.severity,
            "likelihood": row.likelihood,
            "risk_level": _risk_level_from_severity(row.severity),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/projects/{project_id}/safety-score")
def get_project_safety_score(
    project_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "manager", "worker")),
):
    reports = (
        db.query(Report)
        .filter(Report.project_id == project_id, Report.company_id == user.company_id)
        .all()
    )

    if reports:
        hazards = len(reports)
        critical = sum(
            1
            for report in reports
            if (report.severity or 0) >= 4 or (report.likelihood or 0) >= 4
        )
        avg_severity = round(
            sum((report.severity or 1) for report in reports) / hazards
        )
        avg_likelihood = round(
            sum((report.likelihood or 1) for report in reports) / hazards
        )
    else:
        hazards = 0
        critical = 0
        avg_severity = 2
        avg_likelihood = 2

    score = calculate_safety_score(avg_severity, avg_likelihood)
    recommendations = critical * 2 if hazards else 0

    return {
        "project_id": project_id,
        "score": score,
        "risk_level": _risk_level_from_score(score),
        "hazards": hazards,
        "critical": critical,
        "recommendations": recommendations,
    }


# Download Report
@router.get("/download-report")
def download_report(
    file_name: str,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):

    file_path = os.path.join(STORAGE_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    log_activity(
        db,
        user.user_id,
        "Downloaded safety report",
        event_type="user",
        details=f"Downloaded file {file_name}",
        company_id=user.company_id,
    )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/pdf"
    )
