import csv
import io
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.database.models import Project, Report
from backend.services.integration_service import (
    create_api_key,
    create_endpoint,
    delete_endpoint,
    dispatch_event,
    list_api_keys,
    list_endpoints,
    resolve_company_from_api_key,
    revoke_api_key,
)

router = APIRouter(tags=["Integrations"])


class EndpointCreate(BaseModel):
    integration_type: Literal["email", "slack", "teams", "webhook"]
    target: str
    name: str | None = None
    secret: str | None = None
    is_active: bool = True


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class TestEventPayload(BaseModel):
    title: str = "Integration test event"
    body: str = "This is a test event from the AI Safety Platform integrations module."



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def _to_endpoint_dict(endpoint) -> dict:
    return {
        "id": endpoint.id,
        "integration_type": endpoint.integration_type.value,
        "name": endpoint.name,
        "target": endpoint.target,
        "is_active": bool(endpoint.is_active),
        "created_at": endpoint.created_at.isoformat() if endpoint.created_at else None,
        "updated_at": endpoint.updated_at.isoformat() if endpoint.updated_at else None,
    }



def _require_external_company_id(db: Session, x_api_key: str | None, authorization: str | None) -> int:
    raw_key = x_api_key
    if not raw_key and authorization and authorization.lower().startswith("bearer "):
        raw_key = authorization.split(" ", 1)[1].strip()

    company_id = resolve_company_from_api_key(db, raw_key)
    if not company_id:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return company_id


@router.post("/integrations/endpoints", status_code=201)
def add_integration_endpoint(
    payload: EndpointCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    endpoint = create_endpoint(
        db,
        company_id=user.company_id,
        integration_type=payload.integration_type,
        target=payload.target,
        name=payload.name,
        secret=payload.secret,
        is_active=payload.is_active,
    )
    return _to_endpoint_dict(endpoint)


@router.get("/integrations/endpoints")
def get_integration_endpoints(
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return [_to_endpoint_dict(item) for item in list_endpoints(db, company_id=user.company_id)]


@router.delete("/integrations/endpoints/{endpoint_id}")
def remove_integration_endpoint(
    endpoint_id: int,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    deleted = delete_endpoint(db, company_id=user.company_id, endpoint_id=endpoint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration endpoint not found")
    return {"deleted": endpoint_id}


@router.post("/integrations/api-keys", status_code=201)
def create_integration_api_key(
    payload: ApiKeyCreate,
    user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return create_api_key(db, company_id=user.company_id, name=payload.name)


@router.get("/integrations/api-keys")
def get_integration_api_keys(
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return list_api_keys(db, company_id=user.company_id)


@router.delete("/integrations/api-keys/{key_id}")
def revoke_integration_api_key(
    key_id: int,
    user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    revoked = revoke_api_key(db, company_id=user.company_id, key_id=key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": key_id}


@router.post("/integrations/test-event")
def trigger_test_event(
    payload: TestEventPayload,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    results = dispatch_event(
        db,
        company_id=user.company_id,
        event="integration_test",
        title=payload.title,
        body=payload.body,
        payload={"requested_by": user.username},
    )
    return {"results": results}


@router.get("/integrations/exports/reports")
def export_reports(
    format: Literal["csv", "excel"] = Query("csv"),
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report)
        .filter(Report.company_id == user.company_id)
        .order_by(Report.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "project_id", "content", "severity", "likelihood", "created_at"])
    for report in reports:
        writer.writerow(
            [
                report.id,
                report.project_id,
                report.content or "",
                report.severity,
                report.likelihood,
                report.created_at.isoformat() if report.created_at else "",
            ]
        )

    output.seek(0)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if format == "excel":
        media_type = "application/vnd.ms-excel"
        filename = f"reports_{timestamp}.xls"
    else:
        media_type = "text/csv"
        filename = f"reports_{timestamp}.csv"

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([output.getvalue()]), media_type=media_type, headers=headers)


@router.get("/external/projects")
def external_list_projects(
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    company_id = _require_external_company_id(db, x_api_key, authorization)
    rows = (
        db.query(Project)
        .filter(Project.company_id == company_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "name": row.name,
            "description": row.description or "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/external/reports")
def external_list_reports(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    company_id = _require_external_company_id(db, x_api_key, authorization)
    rows = (
        db.query(Report)
        .filter(Report.company_id == company_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "project_id": row.project_id,
            "hazard": row.content or "",
            "severity": row.severity,
            "likelihood": row.likelihood,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/external/hazards")
def external_list_hazards(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    company_id = _require_external_company_id(db, x_api_key, authorization)
    rows = (
        db.query(Report)
        .filter(Report.company_id == company_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "project_id": row.project_id,
            "hazard_description": row.content or "",
            "risk": {
                "severity": row.severity,
                "likelihood": row.likelihood,
            },
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
