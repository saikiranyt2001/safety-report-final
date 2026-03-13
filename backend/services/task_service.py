from datetime import datetime

from sqlalchemy.orm import Session

from backend.database.models import HazardTask, Project, TaskPriorityEnum, TaskStatusEnum, User


# ---- helpers ----

def _task_to_dict(task: HazardTask) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description or "",
        "hazard_type": task.hazard_type or "",
        "priority": task.priority.value if task.priority else "medium",
        "status": task.status.value if task.status else "open",
        "assigned_to_id": task.assigned_to_id,
        "assigned_to": task.assigned_to.username if task.assigned_to else None,
        "created_by": task.created_by.username if task.created_by else None,
        "project_id": task.project_id,
        "project_name": task.project.name if task.project else None,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "resolved_at": task.resolved_at.isoformat() if task.resolved_at else None,
        "proof_notes": task.proof_notes or "",
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _parse_priority(value: str) -> TaskPriorityEnum:
    try:
        return TaskPriorityEnum(value.lower())
    except ValueError:
        return TaskPriorityEnum.medium


# ---- CRUD ----

def create_task(
    db: Session,
    company_id: int | None,
    title: str,
    description: str = "",
    hazard_type: str = "",
    priority: str = "medium",
    assigned_to_id: int | None = None,
    created_by_id: int | None = None,
    project_id: int | None = None,
    deadline: datetime | None = None,
) -> HazardTask:
    assigned_user = None
    project = None

    if assigned_to_id is not None:
        assigned_user = (
            db.query(User)
            .filter(User.id == assigned_to_id, User.company_id == company_id)
            .first()
        )
        if not assigned_user:
            assigned_to_id = None

    if project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.company_id == company_id)
            .first()
        )
        if not project:
            project_id = None

    task = HazardTask(
        company_id=company_id,
        title=title,
        description=description,
        hazard_type=hazard_type,
        priority=_parse_priority(priority),
        status=TaskStatusEnum.open,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
        project_id=project_id,
        deadline=deadline,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    company_id: int | None,
    status: str | None = None,
    assigned_to_id: int | None = None,
    project_id: int | None = None,
) -> list[HazardTask]:
    q = db.query(HazardTask).filter(HazardTask.company_id == company_id)
    if status:
        try:
            q = q.filter(HazardTask.status == TaskStatusEnum(status))
        except ValueError:
            pass
    if assigned_to_id:
        q = q.filter(HazardTask.assigned_to_id == assigned_to_id)
    if project_id:
        q = q.filter(HazardTask.project_id == project_id)
    return q.order_by(HazardTask.created_at.desc()).all()


def get_task(db: Session, company_id: int | None, task_id: int) -> HazardTask | None:
    return (
        db.query(HazardTask)
        .filter(HazardTask.id == task_id, HazardTask.company_id == company_id)
        .first()
    )


def assign_task(db: Session, company_id: int | None, task_id: int, user_id: int) -> HazardTask | None:
    task = get_task(db, company_id, task_id)
    if not task:
        return None
    assignee = (
        db.query(User)
        .filter(User.id == user_id, User.company_id == company_id)
        .first()
    )
    if not assignee:
        return None
    task.assigned_to_id = user_id
    if task.status == TaskStatusEnum.open:
        task.status = TaskStatusEnum.in_progress
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def update_status(
    db: Session,
    company_id: int | None,
    task_id: int,
    new_status: str,
    proof_notes: str = "",
) -> HazardTask | None:
    task = get_task(db, company_id, task_id)
    if not task:
        return None
    try:
        task.status = TaskStatusEnum(new_status)
    except ValueError:
        return None
    if new_status in ("resolved", "closed"):
        task.resolved_at = datetime.utcnow()
        if proof_notes:
            task.proof_notes = proof_notes
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, company_id: int | None, task_id: int) -> HazardTask | None:
    task = get_task(db, company_id, task_id)
    if task:
        db.delete(task)
        db.commit()
    return task


def task_summary(db: Session, company_id: int | None) -> dict:
    all_tasks = db.query(HazardTask).filter(HazardTask.company_id == company_id).all()
    counts = {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
    for t in all_tasks:
        key = t.status.value if t.status else "open"
        counts[key] = counts.get(key, 0) + 1
    return {"total": len(all_tasks), **counts}
