from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import incident_service
from backend.services import task_service
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_incident_reported

router = APIRouter(tags=["Incidents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class IncidentCreate(BaseModel):
    project_id: Optional[int] = None
    incident_type: str
    location: str = ""
    description: str
    severity: str = "low"
    immediate_action: str = ""


class IncidentInvestigationPayload(BaseModel):
    root_cause: str
    corrective_action: str
    contributing_factor: str = ""
    create_task: bool = False
    task_priority: str = "high"
    assign_to_id: Optional[int] = None


@router.get("/incidents/summary")
def get_incident_summary(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return incident_service.incident_summary(db, company_id=user.company_id)


@router.post("/incidents", status_code=201)
def create_incident(
    payload: IncidentCreate,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    incident = incident_service.create_incident(
        db,
        company_id=user.company_id,
        project_id=payload.project_id,
        incident_type=payload.incident_type,
        location=payload.location,
        description=payload.description,
        severity=payload.severity,
        immediate_action=payload.immediate_action,
        reported_by=user.user_id,
    )

    log_activity(
        db,
        user.user_id,
        "Reported incident",
        event_type="incident",
        details=f"Incident #{incident.id}: {payload.incident_type}",
        company_id=user.company_id,
    )

    notify_incident_reported(
        db,
        company_id=user.company_id,
        incident_id=incident.id,
        incident_type=incident.incident_type,
        severity=getattr(incident.severity, "value", str(incident.severity)),
    )

    return incident_service._incident_to_dict(incident)


@router.get("/incidents")
def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    _user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    incidents = incident_service.list_incidents(
        db,
        company_id=_user.company_id,
        status=status,
        severity=severity,
        project_id=project_id,
    )
    return [incident_service._incident_to_dict(item) for item in incidents]


@router.put("/incidents/{incident_id}/investigation")
def update_investigation(
    incident_id: int,
    payload: IncidentInvestigationPayload,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    incident = incident_service.upsert_investigation(
        db,
        company_id=user.company_id,
        incident_id=incident_id,
        root_cause=payload.root_cause,
        corrective_action=payload.corrective_action,
        contributing_factor=payload.contributing_factor,
        investigated_by_id=user.user_id,
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    log_activity(
        db,
        user.user_id,
        "Updated incident investigation",
        event_type="incident",
        details=f"Incident #{incident_id} investigation updated",
        company_id=user.company_id,
    )

    if payload.create_task:
        follow_up_task = task_service.create_task(
            db,
            company_id=user.company_id,
            title=f"Corrective action for INC-{incident.id}: {incident.incident_type}",
            description=payload.corrective_action,
            hazard_type=incident.incident_type,
            priority=payload.task_priority,
            assigned_to_id=payload.assign_to_id,
            created_by_id=user.user_id,
            project_id=incident.project_id,
        )
        log_activity(
            db,
            user.user_id,
            "Created corrective task from incident",
            event_type="incident",
            details=f"Incident #{incident.id} linked task #{follow_up_task.id}",
            company_id=user.company_id,
        )

    return incident_service._incident_to_dict(incident)


@router.put("/incidents/{incident_id}/close")
def close_incident(
    incident_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    incident = incident_service.close_incident(db, user.company_id, incident_id)
    if not incident:
        raise HTTPException(
            status_code=400,
            detail="Incident not found or investigation not completed",
        )

    log_activity(
        db,
        user.user_id,
        "Closed incident",
        event_type="incident",
        details=f"Incident #{incident_id} closed",
        company_id=user.company_id,
    )

    return incident_service._incident_to_dict(incident)
