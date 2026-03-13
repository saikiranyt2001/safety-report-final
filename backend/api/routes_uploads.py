from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import FileResponse
import os
import uuid
from fastapi import Depends

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services.activity_service import log_activity
from backend.vision.image_analyzer import ImageAnalyzer

router = APIRouter()

UPLOAD_DIR = "storage/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# Upload Inspection File
# -------------------------
@router.post(
    "/upload-inspection",
    tags=["Inspections"],
    summary="Upload inspection file"
)
async def upload_inspection(
    project_id: int = Query(...),
    file: UploadFile = File(...),
    user=Depends(require_roles("admin", "manager", "worker")),
    db=Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_location = os.path.join(UPLOAD_DIR, unique_name)

    with open(file_location, "wb") as f:
        f.write(await file.read())

    log_activity(
        db,
        user.user_id,
        "Uploaded inspection image",
        event_type="user",
        details=f"Uploaded {file.filename} for project {project_id}",
    )

    return {
        "project_id": project_id,
        "filename": unique_name,
        "location": file_location
    }


@router.post(
    "/analyze-image",
    tags=["Vision"],
    summary="Analyze safety image and return hazard detections"
)
async def analyze_image(
    file: UploadFile = File(...),
    user=Depends(require_roles("admin", "manager", "worker")),
    db=Depends(get_db),
):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported")

    tmp_name = f"analyze_{uuid.uuid4()}_{file.filename}"
    tmp_path = os.path.join(UPLOAD_DIR, tmp_name)

    try:
        with open(tmp_path, "wb") as temp_file:
            temp_file.write(await file.read())

        analyzer = ImageAnalyzer()
        result = analyzer.analyze(tmp_path)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        detections = result.get("detections", [])
        hazard_count = len(detections)
        log_activity(
            db,
            user.user_id,
            "Hazard detection completed",
            event_type="alert" if hazard_count else "system",
            details=f"AI detected {hazard_count} hazards from {file.filename}",
        )

        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# -------------------------
# Download Generated Report
# -------------------------
@router.get(
    "/download-report/{report_id}",
    tags=["Reports"],
    summary="Download report"
)
async def download_report(
    report_id: int,
    user=Depends(require_roles("admin", "manager", "worker")),
    db=Depends(get_db),
):
    file_path = os.path.join(UPLOAD_DIR, f"report_{report_id}.pdf")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    log_activity(
        db,
        user.user_id,
        "Downloaded generated report",
        event_type="user",
        details=f"Downloaded report_{report_id}.pdf",
    )

    return FileResponse(
        path=file_path,
        filename=f"report_{report_id}.pdf",
        media_type="application/pdf"
    )