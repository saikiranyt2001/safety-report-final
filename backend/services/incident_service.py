from datetime import datetime

from sqlalchemy.orm import Session

from backend.database.models import (
    Incident,
    IncidentInvestigation,
    Project,
    IncidentSeverityEnum,
    IncidentStatusEnum,
)


def _parse_severity(value: str) -> IncidentSeverityEnum:
    try:
        return IncidentSeverityEnum(value.lower())
    except ValueError:
        return IncidentSeverityEnum.low


def _parse_status(value: str) -> IncidentStatusEnum:
    try:
        return IncidentStatusEnum(value.lower())
    except ValueError:
        return IncidentStatusEnum.open


def _investigation_to_dict(inv: IncidentInvestigation | None) -> dict | None:
    if not inv:
        return None
    return {
        "id": inv.id,
        "incident_id": inv.incident_id,
        "root_cause": inv.root_cause,
        "corrective_action": inv.corrective_action,
        "contributing_factor": inv.contributing_factor or "",
        "investigated_by_id": inv.investigated_by_id,
        "investigated_by": inv.investigated_by.username if inv.investigated_by else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
    }


def _incident_to_dict(incident: Incident) -> dict:
    return {
        "id": incident.id,
        "project_id": incident.project_id,
        "reported_by": incident.reported_by,
        "reported_by_name": incident.reporter.username if incident.reporter else None,
        "incident_type": incident.incident_type,
        "location": incident.location or "",
        "description": incident.description,
        "immediate_action": incident.immediate_action or "",
        "severity": incident.severity.value if incident.severity else "low",
        "status": incident.status.value if incident.status else "open",
        "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "investigation": _investigation_to_dict(incident.investigation),
    }


def create_incident(
    db: Session,
    company_id: int | None,
    incident_type: str,
    description: str,
    severity: str = "low",
    location: str = "",
    immediate_action: str = "",
    project_id: int | None = None,
    reported_by: int | None = None,
) -> Incident:
    if project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.company_id == company_id)
            .first()
        )
        if not project:
            project_id = None

    incident = Incident(
        company_id=company_id,
        project_id=project_id,
        reported_by=reported_by,
        incident_type=incident_type,
        description=description,
        severity=_parse_severity(severity),
        location=location,
        immediate_action=immediate_action,
        status=IncidentStatusEnum.open,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(
    db: Session,
    company_id: int | None,
    status: str | None = None,
    severity: str | None = None,
    project_id: int | None = None,
) -> list[Incident]:
    query = db.query(Incident).filter(Incident.company_id == company_id)

    if status:
        query = query.filter(Incident.status == _parse_status(status))
    if severity:
        query = query.filter(Incident.severity == _parse_severity(severity))
    if project_id:
        query = query.filter(Incident.project_id == project_id)

    return query.order_by(Incident.created_at.desc()).all()


def get_incident(db: Session, company_id: int | None, incident_id: int) -> Incident | None:
    return (
        db.query(Incident)
        .filter(Incident.id == incident_id, Incident.company_id == company_id)
        .first()
    )


def upsert_investigation(
    db: Session,
    company_id: int | None,
    incident_id: int,
    root_cause: str,
    corrective_action: str,
    investigated_by_id: int | None,
    contributing_factor: str = "",
) -> Incident | None:
    incident = get_incident(db, company_id, incident_id)
    if not incident:
        return None

    investigation = (
        db.query(IncidentInvestigation)
        .filter(IncidentInvestigation.incident_id == incident_id)
        .first()
    )

    if not investigation:
        investigation = IncidentInvestigation(
            incident_id=incident_id,
            root_cause=root_cause,
            corrective_action=corrective_action,
            contributing_factor=contributing_factor,
            investigated_by_id=investigated_by_id,
        )
        db.add(investigation)
    else:
        investigation.root_cause = root_cause
        investigation.corrective_action = corrective_action
        investigation.contributing_factor = contributing_factor
        investigation.investigated_by_id = investigated_by_id
        investigation.updated_at = datetime.utcnow()

    incident.status = IncidentStatusEnum.investigating
    incident.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)
    return incident


def close_incident(db: Session, company_id: int | None, incident_id: int) -> Incident | None:
    incident = get_incident(db, company_id, incident_id)
    if not incident:
        return None

    if not incident.investigation:
        return None

    incident.status = IncidentStatusEnum.closed
    incident.closed_at = datetime.utcnow()
    incident.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)
    return incident


def incident_summary(db: Session, company_id: int | None) -> dict:
    incidents = db.query(Incident).filter(Incident.company_id == company_id).all()
    counts = {
        "open": 0,
        "investigating": 0,
        "closed": 0,
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    for item in incidents:
        status_key = item.status.value if item.status else "open"
        severity_key = item.severity.value if item.severity else "low"
        counts[status_key] = counts.get(status_key, 0) + 1
        counts[severity_key] = counts.get(severity_key, 0) + 1

    return {
        "total": len(incidents),
        "open": counts["open"],
        "investigating": counts["investigating"],
        "closed": counts["closed"],
        "low": counts["low"],
        "medium": counts["medium"],
        "high": counts["high"],
        "critical": counts["critical"],
    }
