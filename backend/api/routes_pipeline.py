import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from celery.result import AsyncResult

from backend.tasks.pipeline_tasks import analyze_image_task, safety_pipeline_task
from backend.celery_app import celery_app
from backend.schemas.pipeline_schema import PipelineRequest

from backend.core.limiter import limiter
from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services.activity_service import log_activity
from backend.services.ai_service import ask_ai

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

PIPELINE_UPLOAD_DIR = os.path.join("storage", "reports")
os.makedirs(PIPELINE_UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_legacy_task_status(task: AsyncResult):
    if task.state == "PENDING":
        return {"status": "pending"}

    if task.state == "SUCCESS":
        return {
            "status": "completed",
            "result": task.result,
        }

    if task.state == "FAILURE":
        return {
            "status": "failed",
            "error": str(task.result),
        }

    return {"status": task.state.lower()}


def _serialize_task_state(task: AsyncResult):
    payload = {
        "task_id": task.id,
        "status": task.state,
        "state": task.state,
    }

    if task.state == "SUCCESS":
        payload["result"] = task.result
    elif task.state == "FAILURE":
        payload["error"] = str(task.result)

    return payload


# -----------------------------
# Start AI Safety Pipeline
# -----------------------------
@router.post("/run")
@limiter.limit("10/minute")
async def run_pipeline(
    request: Request,
    payload: PipelineRequest,
    user=Depends(require_roles("admin", "manager")),
    db=Depends(get_db),
):

    company_id = request.state.company_id
    user_id = request.state.user_id

    task = safety_pipeline_task.delay(
        payload.site_type,
        payload.site_data
    )

    log_activity(
        db,
        user.user_id,
        "Started safety inspection pipeline",
        event_type="system",
        details=f"Pipeline task {task.id} started for {payload.site_type}",
        company_id=user.company_id,
    )

    return {
        "task_id": task.id,
        "status": "processing",
        "company_id": company_id,
        "user_id": user_id
    }


@router.post("/analyze-image")
@limiter.limit("20/minute")
async def queue_image_analysis(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_roles("admin", "manager", "worker")),
    db=Depends(get_db),
):

    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported")

    company_id = getattr(request.state, "company_id", user.company_id)
    user_id = getattr(request.state, "user_id", user.user_id)
    unique_name = f"pipeline_{uuid.uuid4()}_{file.filename}"
    image_path = os.path.join(PIPELINE_UPLOAD_DIR, unique_name)

    with open(image_path, "wb") as handle:
        handle.write(await file.read())

    task = analyze_image_task.delay(image_path)

    log_activity(
        db,
        user.user_id,
        "Queued AI image analysis",
        event_type="system",
        details=f"Image analysis task {task.id} queued for {file.filename}",
        company_id=user.company_id,
    )

    return {
        "task_id": task.id,
        "status": "processing",
        "company_id": company_id,
        "user_id": user_id,
        "filename": unique_name,
    }


# -----------------------------
# Check Task Status
# -----------------------------
@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    _user=Depends(require_roles("admin", "manager", "worker")),
):

    task = AsyncResult(task_id, app=celery_app)

    return _serialize_legacy_task_status(task)


@router.get("/task-status/{task_id}")
async def get_image_task_status(
    task_id: str,
    _user=Depends(require_roles("admin", "manager", "worker")),
):

    task = AsyncResult(task_id, app=celery_app)

    return _serialize_task_state(task)


@router.post("/ai-chat")
async def ai_chat(
    prompt: str,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    response = ask_ai(prompt)
    return {"response": response}

