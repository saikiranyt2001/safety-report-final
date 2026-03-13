from sqlalchemy.orm import Session

from backend.database.models import ActivityLog, User


def _resolve_company_id(db: Session, user_id: int | None, company_id: int | None) -> int | None:
    if company_id is not None:
        return company_id
    if user_id is None:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user.company_id if user else None


def log_activity(
    db: Session,
    user_id: int | None,
    action: str,
    event_type: str = "user",
    details: str | None = None,
    company_id: int | None = None,
):
    activity = ActivityLog(
        user_id=user_id,
        company_id=_resolve_company_id(db, user_id, company_id),
        action=action,
        event_type=event_type,
        details=details,
    )

    db.add(activity)
    db.commit()
    db.refresh(activity)

    return activity


def get_recent_activity_logs(db: Session, company_id: int | None, limit: int = 100):
    logs = (
        db.query(ActivityLog)
        .outerjoin(User, ActivityLog.user_id == User.id)
        .filter(ActivityLog.company_id == company_id)
        .order_by(ActivityLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "user": log.user.username if log.user else "system",
            "action": log.action,
            "type": log.event_type,
            "details": log.details or "",
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]