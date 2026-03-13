from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services import training_service
from backend.services.activity_service import log_activity
from backend.services.notification_service import notify_training_expiring

router = APIRouter(tags=["Training"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CourseCreate(BaseModel):
    name: str
    description: str = ""
    validity_months: int = 12


class TrainingAssign(BaseModel):
    user_id: int
    course_id: int
    completed_date: Optional[datetime] = None
    certificate_ref: str = ""


class TrainingComplete(BaseModel):
    completed_date: Optional[datetime] = None
    certificate_ref: str = ""


@router.post("/training/courses", status_code=201)
def create_course(
    payload: CourseCreate,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    course = training_service.create_course(
        db,
        company_id=user.company_id,
        name=payload.name,
        description=payload.description,
        validity_months=payload.validity_months,
    )
    log_activity(
        db,
        user.user_id,
        "Created training course",
        event_type="training",
        details=f"Course '{payload.name}' ({payload.validity_months} months)",
        company_id=user.company_id,
    )
    return training_service._course_to_dict(course)


@router.get("/training/courses")
def list_courses(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    courses = training_service.list_courses(db, company_id=user.company_id)
    return [training_service._course_to_dict(course) for course in courses]


@router.post("/training/assign", status_code=201)
def assign_training(
    payload: TrainingAssign,
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    record = training_service.assign_training(
        db,
        company_id=user.company_id,
        user_id=payload.user_id,
        course_id=payload.course_id,
        assigned_by_id=user.user_id,
        completed_date=payload.completed_date,
        certificate_ref=payload.certificate_ref,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Course not found")

    log_activity(
        db,
        user.user_id,
        "Assigned training",
        event_type="training",
        details=f"Assigned course {payload.course_id} to user {payload.user_id}",
        company_id=user.company_id,
    )
    return training_service._record_to_dict(record)


@router.put("/training/records/{record_id}/complete")
def complete_training(
    record_id: int,
    payload: TrainingComplete,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    record = training_service.complete_training(
        db,
        company_id=user.company_id,
        record_id=record_id,
        completed_date=payload.completed_date,
        certificate_ref=payload.certificate_ref,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Training record not found")

    log_activity(
        db,
        user.user_id,
        "Completed training",
        event_type="training",
        details=f"Record {record_id} completed",
        company_id=user.company_id,
    )
    return training_service._record_to_dict(record)


@router.get("/training/records")
def list_training_records(
    my_records: bool = Query(False),
    status: Optional[str] = Query(None),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    filter_user_id = user.user_id if my_records else None
    records = training_service.list_records(
        db,
        company_id=user.company_id,
        user_id=filter_user_id,
        status=status,
    )
    return [training_service._record_to_dict(record) for record in records]


@router.get("/training/alerts")
def get_training_alerts(
    within_days: int = Query(30, ge=1, le=180),
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    alerts = training_service.expiring_alerts(db, company_id=user.company_id, within_days=within_days)
    for alert in alerts:
        notify_training_expiring(
            db,
            company_id=user.company_id,
            worker=alert.get("worker", "Unknown"),
            training=alert.get("training", "Unknown"),
            days_to_expiry=alert.get("days_to_expiry", within_days),
        )
    return alerts


@router.get("/training/summary")
def get_training_summary(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    return training_service.training_summary(db, company_id=user.company_id)
