
from fastapi import APIRouter, Depends, Request
from celery.result import AsyncResult

from backend.tasks.pipeline_tasks import safety_pipeline_task
from backend.celery_app import celery_app
from backend.schemas.pipeline_schema import PipelineRequest

from backend.core.limiter import limiter
from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services.activity_service import log_activity
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# -----------------------------
# Check Task Status
# -----------------------------
@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    _user=Depends(require_roles("admin", "manager", "worker")),
):

    task = AsyncResult(task_id, app=celery_app)

    if task.state == "PENDING":
        return {"status": "pending"}

    elif task.state == "SUCCESS":
        return {
            "status": "completed",
            "result": task.result
        }

    elif task.state == "FAILURE":
        return {
            "status": "failed",
            "error": str(task.result)
        }

    return {"status": task.state}

