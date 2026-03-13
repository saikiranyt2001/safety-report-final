from datetime import datetime

from sqlalchemy.orm import Session

from backend.agents.compliance_agent import evaluate_rule, find_matching_regulations
from backend.database.models import ComplianceCheck, ComplianceRule, Project
from backend.services import task_service


VALID_COMPLIANCE_STATUSES = {"compliant", "violated"}


def _normalize_status(value: str | None) -> str:
    normalized = (value or "compliant").strip().lower()
    return normalized if normalized in VALID_COMPLIANCE_STATUSES else "compliant"


def _rule_to_dict(rule: ComplianceRule) -> dict:
    latest_check = rule.checks[0] if rule.checks else None
    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "description": rule.description,
        "regulation_source": rule.regulation_source,
        "category": rule.category or "",
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "latest_status": latest_check.status if latest_check else None,
        "latest_checked_at": latest_check.checked_at.isoformat() if latest_check else None,
        "recommended_action": latest_check.recommended_action if latest_check else "",
    }


def _check_to_dict(check: ComplianceCheck) -> dict:
    return {
        "id": check.id,
        "rule_id": check.rule_id,
        "rule_name": check.rule.rule_name if check.rule else None,
        "project_id": check.project_id,
        "status": check.status,
        "location": check.location or "",
        "evidence": check.evidence or "",
        "recommended_action": check.recommended_action or "",
        "maintenance_task_id": check.maintenance_task_id,
        "checked_at": check.checked_at.isoformat() if check.checked_at else None,
        "checked_by": check.checked_by.username if check.checked_by else None,
        "regulation_source": check.rule.regulation_source if check.rule else None,
        "category": check.rule.category if check.rule else None,
    }


def add_rule(
    db: Session,
    company_id: int | None,
    rule_name: str,
    description: str,
    regulation_source: str,
    category: str = "",
) -> ComplianceRule:
    rule = ComplianceRule(
        company_id=company_id,
        rule_name=rule_name,
        description=description,
        regulation_source=regulation_source,
        category=category,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session, company_id: int | None) -> list[ComplianceRule]:
    return (
        db.query(ComplianceRule)
        .filter(ComplianceRule.company_id == company_id)
        .order_by(ComplianceRule.created_at.desc())
        .all()
    )


def get_rule(db: Session, company_id: int | None, rule_id: int) -> ComplianceRule | None:
    return (
        db.query(ComplianceRule)
        .filter(ComplianceRule.id == rule_id, ComplianceRule.company_id == company_id)
        .first()
    )


def create_check(
    db: Session,
    company_id: int | None,
    rule_id: int,
    checked_by_id: int | None,
    project_id: int | None = None,
    status: str | None = None,
    location: str = "",
    evidence: str = "",
    observation: str = "",
    create_task: bool = False,
    task_priority: str = "high",
    assign_to_id: int | None = None,
) -> ComplianceCheck | None:
    rule = get_rule(db, company_id, rule_id)
    if not rule:
        return None

    if project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.company_id == company_id)
            .first()
        )
        if not project:
            project_id = None

    evaluation = evaluate_rule(rule.rule_name, observation or evidence or rule.description)
    resolved_status = _normalize_status(status or evaluation["status"])
    recommended_action = evaluation["recommended_action"]
    maintenance_task_id = None

    if create_task and resolved_status == "violated":
        task = task_service.create_task(
            db,
            company_id=company_id,
            title=f"Compliance corrective action: {rule.rule_name}",
            description=recommended_action,
            hazard_type=f"Compliance: {rule.regulation_source}",
            priority=task_priority,
            assigned_to_id=assign_to_id,
            created_by_id=checked_by_id,
            project_id=project_id,
        )
        maintenance_task_id = task.id

    check = ComplianceCheck(
        company_id=company_id,
        rule_id=rule_id,
        project_id=project_id,
        checked_by_id=checked_by_id,
        status=resolved_status,
        location=location,
        evidence=evidence or observation,
        recommended_action=recommended_action,
        maintenance_task_id=maintenance_task_id,
        checked_at=datetime.utcnow(),
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def get_report(db: Session, company_id: int | None, project_id: int | None = None) -> list[dict]:
    rules = list_rules(db, company_id=company_id)
    report = []
    for rule in rules:
        checks = rule.checks
        if project_id is not None:
            checks = [item for item in checks if item.project_id == project_id]
        latest = checks[0] if checks else None
        report.append(
            {
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "description": rule.description,
                "regulation_source": rule.regulation_source,
                "category": rule.category or "",
                "status": latest.status if latest else "not_checked",
                "location": latest.location if latest else "",
                "evidence": latest.evidence if latest else "",
                "recommended_action": latest.recommended_action if latest else "",
                "checked_at": latest.checked_at.isoformat() if latest and latest.checked_at else None,
                "maintenance_task_id": latest.maintenance_task_id if latest else None,
            }
        )
    return report


def compliance_summary(db: Session, company_id: int | None) -> dict:
    report = get_report(db, company_id=company_id)
    counts = {"compliant": 0, "violated": 0, "not_checked": 0}
    for item in report:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"total": len(report), **counts}


def suggested_rules(query: str) -> list[dict]:
    return find_matching_regulations(query)
