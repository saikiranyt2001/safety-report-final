from fastapi import APIRouter, Body, Query, File, UploadFile, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import uuid

from backend.rag.rag_engine import RAGEngine
from backend.vision.image_analyzer import ImageAnalyzer
from backend.database.database import SessionLocal
from backend.database.models import Project, Report
from backend.services.report_service import generate_report_task

router = APIRouter(tags=["Reports"])

STORAGE_DIR = "storage/reports"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Create Project
# -----------------------------
@router.post("/create-project")
async def create_project(
    project_name: str = Body(...),
    location: str = Body(...),
    db: Session = Depends(get_db)
):
    project = Project(name=project_name, description=location)

    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "location": project.description
    }

# -----------------------------
# Report History
# -----------------------------
@router.get("/reports")
async def get_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).all()

    return [
        {
            "report_id": r.id,
            "project": r.project.name if r.project else None,
            "created_at": r.created_at.strftime("%Y-%m-%d")
        }
        for r in reports
    ]

# -----------------------------
# AI Chat About Report
# -----------------------------
@router.post("/report-chat")
async def report_chat(
    report_id: int = Body(...),
    message: str = Body(...),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    answer = f"AI: The report for project '{report.project.name if report.project else 'Unknown'}' says: {report.content}"

    return {"answer": answer}

# -----------------------------
# RAG Report Generation
# -----------------------------
@router.post("/generate-rag-report")
async def generate_rag_report(user_request: str = Body(...)):
    rag = RAGEngine()

    context = rag.retrieve(user_request)
    report = rag.generate_report(context, user_request)

    return {"report": report}

# -----------------------------
# Download PDF Report
# -----------------------------
@router.get("/download-report/{report_id}")
async def download_report(report_id: int):
    filename = os.path.join(STORAGE_DIR, f"report_{report_id}.pdf")

    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=filename,
        filename=f"report_{report_id}.pdf",
        media_type="application/pdf"
    )

# -----------------------------
# Image Hazard Analysis
# -----------------------------
@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    image_path = os.path.join(STORAGE_DIR, unique_name)

    with open(image_path, "wb") as f:
        f.write(await file.read())

    analyzer = ImageAnalyzer()
    hazards = analyzer.analyze(image_path)

    return {"hazards": hazards}

# -----------------------------
# Generate Report (Celery Task)
# -----------------------------
@router.post("/generate-report")
async def generate_report(
    report_type: str = Query(...),
    project_id: int = Query(...)
):
    task = generate_report_task.delay({
        "report_type": report_type,
        "project_id": project_id
    })

    return {
        "task_id": task.id,
        "status": "queued"
    }
