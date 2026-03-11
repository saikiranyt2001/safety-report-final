from fastapi import APIRouter, File, UploadFile, Query, HTTPException
from fastapi.responses import FileResponse
import os
import uuid

router = APIRouter()

UPLOAD_DIR = "storage/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]

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
    file: UploadFile = File(...)
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

    return {
        "project_id": project_id,
        "filename": unique_name,
        "location": file_location
    }

# -------------------------
# Download Generated Report
# -------------------------
@router.get(
    "/download-report/{report_id}",
    tags=["Reports"],
    summary="Download report"
)
async def download_report(report_id: int):

    file_path = os.path.join(UPLOAD_DIR, f"report_{report_id}.pdf")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    return FileResponse(
        path=file_path,
        filename=f"report_{report_id}.pdf",
        media_type="application/pdf"
    )