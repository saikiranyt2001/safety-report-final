from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import task_service
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_task_assigned

router = APIRouter(tags=["Tasks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- Pydantic schemas ----

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    hazard_type: str = ""
    priority: str = "medium"
    assigned_to_id: Optional[int] = None
    project_id: Optional[int] = None
    deadline: Optional[datetime] = None


class TaskAssign(BaseModel):
    user_id: int


class TaskStatusUpdate(BaseModel):
    status: str                  # open | in_progress | resolved | closed
    proof_notes: str = ""


# ---- Endpoints ----

@router.get("/tasks/summary")
def get_task_summary(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return task_service.task_summary(db, company_id=user.company_id)


@router.get("/tasks")
def list_tasks(
    status: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    my_tasks: bool = Query(False),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    assigned_filter = user.user_id if my_tasks else None
    tasks = task_service.list_tasks(
        db,
        company_id=user.company_id,
        status=status,
        assigned_to_id=assigned_filter,
        project_id=project_id,
    )
    return [task_service._task_to_dict(t) for t in tasks]


@router.post("/tasks", status_code=201)
def create_task(
    payload: TaskCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    task = task_service.create_task(
        db,
        company_id=user.company_id,
        title=payload.title,
        description=payload.description,
        hazard_type=payload.hazard_type,
        priority=payload.priority,
        assigned_to_id=payload.assigned_to_id,
        created_by_id=user.user_id,
        project_id=payload.project_id,
        deadline=payload.deadline,
    )
    log_activity(
        db,
        user.user_id,
        "Created hazard task",
        event_type="user",
        details=f"Task '{payload.title}' created (priority: {payload.priority})",
        company_id=user.company_id,
    )

    if task.assigned_to_id:
        notify_task_assigned(
            db,
            company_id=user.company_id,
            task_id=task.id,
            task_title=task.title,
            assigned_to=task.assigned_to.username if task.assigned_to else str(task.assigned_to_id),
        )

    return task_service._task_to_dict(task)


@router.get("/tasks/{task_id}")
def get_task(
    task_id: int,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    task = task_service.get_task(db, user.company_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_service._task_to_dict(task)


@router.put("/tasks/{task_id}/assign")
def assign_task(
    task_id: int,
    payload: TaskAssign,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    task = task_service.assign_task(db, user.company_id, task_id, payload.user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    log_activity(
        db,
        user.user_id,
        "Assigned hazard task",
        event_type="user",
        details=f"Task {task_id} assigned to user {payload.user_id}",
        company_id=user.company_id,
    )

    notify_task_assigned(
        db,
        company_id=user.company_id,
        task_id=task.id,
        task_title=task.title,
        assigned_to=task.assigned_to.username if task.assigned_to else str(payload.user_id),
    )

    return task_service._task_to_dict(task)


@router.put("/tasks/{task_id}/status")
def update_status(
    task_id: int,
    payload: TaskStatusUpdate,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    task = task_service.update_status(
        db,
        company_id=user.company_id,
        task_id=task_id,
        new_status=payload.status,
        proof_notes=payload.proof_notes,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or invalid status")
    log_activity(
        db,
        user.user_id,
        f"Updated task status to {payload.status}",
        event_type="user",
        details=f"Task {task_id} → {payload.status}",
        company_id=user.company_id,
    )
    return task_service._task_to_dict(task)


@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    task = task_service.delete_task(db, user.company_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    log_activity(
        db,
        user.user_id,
        "Deleted hazard task",
        event_type="user",
        details=f"Task {task_id} deleted",
        company_id=user.company_id,
    )
    return {"deleted": task_id}
