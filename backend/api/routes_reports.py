import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
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


# Generate Report
@router.post("/generate-report")
async def generate_report(project_id: int):

    hazards = "Slip hazard near machine"
    risk_score = "High"

    task = generate_report_task.delay(project_id, hazards, risk_score)

    return {
        "message": "Report generation started",
        "task_id": task.id
    }


# Download Report
@router.get("/download-report")
def download_report(file_name: str):

    file_path = os.path.join(STORAGE_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/pdf"
    )