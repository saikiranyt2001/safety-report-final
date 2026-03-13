from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.database.models import TrainingCourse, TrainingRecord, User


def _months_to_days(months: int) -> int:
    # Approximate month length for expiry calculation consistency.
    return max(1, months) * 30


def _compute_status(expiry_date: datetime | None, completed_date: datetime | None) -> tuple[str, int | None]:
    if not completed_date:
        return "pending", None

    if not expiry_date:
        return "valid", None

    now = datetime.utcnow()
    days_to_expiry = (expiry_date.date() - now.date()).days

    if days_to_expiry < 0:
        return "expired", days_to_expiry
    if days_to_expiry <= 30:
        return "expiring_soon", days_to_expiry
    return "valid", days_to_expiry


def _course_to_dict(course: TrainingCourse) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description or "",
        "validity_months": course.validity_months,
        "created_at": course.created_at.isoformat() if course.created_at else None,
    }


def _record_to_dict(record: TrainingRecord) -> dict:
    status, days_to_expiry = _compute_status(record.expiry_date, record.completed_date)
    return {
        "id": record.id,
        "user_id": record.user_id,
        "worker_name": record.user.username if record.user else None,
        "course_id": record.course_id,
        "course_name": record.course.name if record.course else None,
        "assigned_by_id": record.assigned_by_id,
        "assigned_by": record.assigned_by.username if record.assigned_by else None,
        "assigned_at": record.assigned_at.isoformat() if record.assigned_at else None,
        "completed_date": record.completed_date.isoformat() if record.completed_date else None,
        "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
        "certificate_ref": record.certificate_ref or "",
        "status": status,
        "days_to_expiry": days_to_expiry,
    }


def create_course(
    db: Session,
    company_id: int | None,
    name: str,
    description: str,
    validity_months: int,
) -> TrainingCourse:
    course = TrainingCourse(
        company_id=company_id,
        name=name,
        description=description,
        validity_months=max(1, validity_months),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def assign_training(
    db: Session,
    company_id: int | None,
    user_id: int,
    course_id: int,
    assigned_by_id: int | None,
    completed_date: datetime | None = None,
    certificate_ref: str = "",
) -> TrainingRecord | None:
    course = (
        db.query(TrainingCourse)
        .filter(TrainingCourse.id == course_id, TrainingCourse.company_id == company_id)
        .first()
    )
    if not course:
        return None

    user = db.query(User).filter(User.id == user_id, User.company_id == company_id).first()
    if not user:
        return None

    expiry_date = None
    if completed_date:
        expiry_date = completed_date + timedelta(days=_months_to_days(course.validity_months))

    record = TrainingRecord(
        company_id=company_id,
        user_id=user_id,
        course_id=course_id,
        assigned_by_id=assigned_by_id,
        completed_date=completed_date,
        expiry_date=expiry_date,
        certificate_ref=certificate_ref,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def complete_training(
    db: Session,
    company_id: int | None,
    record_id: int,
    completed_date: datetime | None = None,
    certificate_ref: str = "",
) -> TrainingRecord | None:
    record = (
        db.query(TrainingRecord)
        .filter(TrainingRecord.id == record_id, TrainingRecord.company_id == company_id)
        .first()
    )
    if not record:
        return None

    finish_date = completed_date or datetime.utcnow()
    validity_days = _months_to_days(record.course.validity_months if record.course else 12)

    record.completed_date = finish_date
    record.expiry_date = finish_date + timedelta(days=validity_days)
    if certificate_ref:
        record.certificate_ref = certificate_ref
    record.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(record)
    return record


def list_courses(db: Session, company_id: int | None) -> list[TrainingCourse]:
    return (
        db.query(TrainingCourse)
        .filter(TrainingCourse.company_id == company_id)
        .order_by(TrainingCourse.created_at.desc())
        .all()
    )


def list_records(
    db: Session,
    company_id: int | None,
    user_id: int | None = None,
    status: str | None = None,
) -> list[TrainingRecord]:
    records = (
        db.query(TrainingRecord)
        .filter(TrainingRecord.company_id == company_id)
        .order_by(TrainingRecord.assigned_at.desc())
        .all()
    )

    if user_id:
        records = [record for record in records if record.user_id == user_id]

    if status:
        records = [record for record in records if _compute_status(record.expiry_date, record.completed_date)[0] == status]

    return records


def expiring_alerts(db: Session, company_id: int | None, within_days: int = 30) -> list[dict]:
    alerts = []
    for record in list_records(db, company_id=company_id):
        status, days_to_expiry = _compute_status(record.expiry_date, record.completed_date)
        if status == "expiring_soon" and days_to_expiry is not None and days_to_expiry <= within_days:
            alerts.append(
                {
                    "record_id": record.id,
                    "worker": record.user.username if record.user else f"User {record.user_id}",
                    "training": record.course.name if record.course else f"Course {record.course_id}",
                    "days_to_expiry": days_to_expiry,
                    "expiry_date": record.expiry_date.isoformat() if record.expiry_date else None,
                }
            )
    return alerts


def training_summary(db: Session, company_id: int | None) -> dict:
    records = list_records(db, company_id=company_id)
    counts = {
        "total": len(records),
        "valid": 0,
        "expiring_soon": 0,
        "expired": 0,
        "pending": 0,
    }

    for record in records:
        status, _ = _compute_status(record.expiry_date, record.completed_date)
        counts[status] = counts.get(status, 0) + 1

    return counts
