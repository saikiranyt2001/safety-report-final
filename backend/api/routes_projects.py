from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.database.models import Project
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Projects"])


class ProjectCreatePayload(BaseModel):
    project_name: str
    location: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "location": project.description or "",
        "status": "Active",
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@router.get("/projects")
def list_projects(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Project)
        .filter(Project.company_id == user.company_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [_serialize_project(row) for row in rows]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreatePayload,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    project = Project(
        name=payload.project_name.strip(),
        description=payload.location.strip(),
        company_id=user.company_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    log_activity(
        db,
        user.user_id,
        "Created project",
        event_type="user",
        details=f"Created project {project.name}",
        company_id=user.company_id,
    )

    return _serialize_project(project)


@router.post("/create-project", status_code=status.HTTP_201_CREATED)
def create_project_legacy(
    payload: ProjectCreatePayload,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return create_project(payload, user, db)


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.company_id == user.company_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_name = project.name
    db.delete(project)
    db.commit()

    log_activity(
        db,
        user.user_id,
        "Deleted project",
        event_type="user",
        details=f"Deleted project {project_name}",
        company_id=user.company_id,
    )

    return {"deleted": project_id}
