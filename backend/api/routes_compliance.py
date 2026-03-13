from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import compliance_service
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Compliance"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ComplianceRuleCreate(BaseModel):
    rule_name: str
    description: str
    regulation_source: str
    category: str = ""


class ComplianceCheckCreate(BaseModel):
    rule_id: int
    project_id: Optional[int] = None
    status: Optional[str] = None
    location: str = ""
    evidence: str = ""
    observation: str = ""
    create_task: bool = False
    task_priority: str = "high"
    assign_to_id: Optional[int] = None


@router.get("/compliance/summary")
def get_compliance_summary(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return compliance_service.compliance_summary(db, company_id=user.company_id)


@router.get("/compliance/rules")
def list_compliance_rules(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    rules = compliance_service.list_rules(db, company_id=user.company_id)
    return [compliance_service._rule_to_dict(rule) for rule in rules]


@router.post("/compliance/rules", status_code=201)
def add_compliance_rule(
    payload: ComplianceRuleCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    rule = compliance_service.add_rule(
        db,
        company_id=user.company_id,
        rule_name=payload.rule_name,
        description=payload.description,
        regulation_source=payload.regulation_source,
        category=payload.category,
    )
    log_activity(
        db,
        user.user_id,
        "Added compliance rule",
        event_type="compliance",
        details=f"Rule '{payload.rule_name}' added",
        company_id=user.company_id,
    )
    return compliance_service._rule_to_dict(rule)


@router.post("/compliance/check", status_code=201)
def check_compliance(
    payload: ComplianceCheckCreate,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    check = compliance_service.create_check(
        db,
        company_id=user.company_id,
        rule_id=payload.rule_id,
        checked_by_id=user.user_id,
        project_id=payload.project_id,
        status=payload.status,
        location=payload.location,
        evidence=payload.evidence,
        observation=payload.observation,
        create_task=payload.create_task,
        task_priority=payload.task_priority,
        assign_to_id=payload.assign_to_id,
    )
    if not check:
        raise HTTPException(status_code=404, detail="Compliance rule not found")

    details = f"Rule {payload.rule_id} checked: {check.status}"
    if check.maintenance_task_id:
        details += f"; corrective task #{check.maintenance_task_id} created"

    log_activity(
        db,
        user.user_id,
        "Completed compliance check",
        event_type="compliance",
        details=details,
        company_id=user.company_id,
    )
    return compliance_service._check_to_dict(check)


@router.get("/compliance/report")
def get_compliance_report(
    project_id: Optional[int] = Query(None),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return compliance_service.get_report(db, company_id=user.company_id, project_id=project_id)


@router.get("/compliance/suggestions")
def get_compliance_suggestions(
    query: str = Query(..., min_length=2),
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    return compliance_service.suggested_rules(query)
