from backend.celery_app import celery_app
from backend.database.database import SessionLocal
from backend.database.models import Report, Project
import os

STORAGE_DIR = "storage/reports"


@celery_app.task(name="backend.services.report_service.generate_report_task")
def generate_report_task(payload):

    report_type = payload.get("report_type")
    project_id = payload.get("project_id")

    db = SessionLocal()

    try:

        project = db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return {"status": "error", "message": "Project not found"}

        # Example content
        report_content = f"{report_type} report generated for project {project.name}"

        report = Report(
            project_id=project_id,
            content=report_content
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return {
            "status": "generated",
            "report_id": report.id
        }

    finally:
        db.close()