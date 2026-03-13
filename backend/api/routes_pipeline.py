
from fastapi import APIRouter, Request
from celery.result import AsyncResult

from backend.tasks.pipeline_tasks import safety_pipeline_task
from backend.celery_app import celery_app
from backend.schemas.pipeline_schema import PipelineRequest

from backend.core.limiter import limiter
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# -----------------------------
# Start AI Safety Pipeline
# -----------------------------
@router.post("/run")
@limiter.limit("10/minute")
async def run_pipeline(request: Request, payload: PipelineRequest):

    company_id = request.state.company_id
    user_id = request.state.user_id

    task = safety_pipeline_task.delay(
        payload.site_type,
        payload.site_data
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
async def get_task_status(task_id: str):

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

