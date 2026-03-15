import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.database.models import User, UserSettings
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Settings"])


class SettingsUpdatePayload(BaseModel):
    display_name: str = ""
    email: str = ""
    timezone: str = "UTC"
    notify_high_risk: bool = True
    notify_weekly: bool = True
    notify_maintenance: bool = False
    notify_recommendations: bool = True
    current_password: str = ""
    new_password: str = ""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_password(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if settings:
        return settings

    settings = UserSettings(user_id=user_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _serialize_settings(user: User, settings: UserSettings) -> dict:
    return {
        "display_name": settings.display_name or user.username,
        "email": settings.email or "",
        "timezone": settings.timezone or "UTC",
        "notify_high_risk": bool(settings.notify_high_risk),
        "notify_weekly": bool(settings.notify_weekly),
        "notify_maintenance": bool(settings.notify_maintenance),
        "notify_recommendations": bool(settings.notify_recommendations),
        "username": user.username,
    }


@router.get("/settings/me")
def get_my_settings(
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    current_user = db.query(User).filter(User.id == user.user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    settings = _get_or_create_settings(db, current_user.id)
    return _serialize_settings(current_user, settings)


@router.put("/settings/me")
def update_my_settings(
    payload: SettingsUpdatePayload,
    user=Depends(require_roles("admin", "manager", "worker")),
    db: Session = Depends(get_db),
):
    current_user = db.query(User).filter(User.id == user.user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    settings = _get_or_create_settings(db, current_user.id)
    settings.display_name = payload.display_name.strip() or current_user.username
    settings.email = payload.email.strip()
    settings.timezone = payload.timezone.strip() or "UTC"
    settings.notify_high_risk = 1 if payload.notify_high_risk else 0
    settings.notify_weekly = 1 if payload.notify_weekly else 0
    settings.notify_maintenance = 1 if payload.notify_maintenance else 0
    settings.notify_recommendations = 1 if payload.notify_recommendations else 0

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if current_user.password_hash != _hash_password(payload.current_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        current_user.password_hash = _hash_password(payload.new_password)

    db.commit()
    db.refresh(settings)
    db.refresh(current_user)

    log_activity(
        db,
        current_user.id,
        "Updated settings",
        event_type="user",
        details="Updated account settings and preferences",
        company_id=current_user.company_id,
    )

    return {
        "message": "Settings saved successfully.",
        "settings": _serialize_settings(current_user, settings),
    }
