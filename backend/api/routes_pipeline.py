from fastapi import APIRouter, HTTPException
from backend.tasks.pipeline_tasks import run_pipeline_task

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

@router.post("/run/{project_id}")
def run_pipeline(project_id: int):
    task = run_pipeline_task.delay(project_id)
    return {"task_id": task.id, "status": "Pipeline started"}
