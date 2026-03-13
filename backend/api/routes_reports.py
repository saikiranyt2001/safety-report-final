import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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