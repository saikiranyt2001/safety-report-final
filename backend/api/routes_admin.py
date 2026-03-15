from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from pydantic import BaseModel
from ..services.usage_tracker import get_monthly_usage
from backend.core.dependencies import require_role
from backend.core.dependencies import get_database
from backend.core.passwords import hash_password
from backend.services import user_service
from backend.services.account_state_service import get_or_create_account_state, set_user_active
from sqlalchemy.orm import Session
from backend.database.models import RoleEnum, User
from backend.services.activity_service import log_activity

router = APIRouter(tags=["Admin"])


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str = "worker"


class AdminUserUpdate(BaseModel):
    username: str | None = None
    role: str | None = None


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


def _role_from_value(value: str | None) -> RoleEnum:
    try:
        return RoleEnum((value or "worker").strip().lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

def _serialize_user(db: Session, target: User) -> dict:
    state = target.account_state or get_or_create_account_state(db, target)
    return {
        "id": target.id,
        "username": target.username,
        "role": target.role.value if hasattr(target.role, "value") else str(target.role),
        "company_id": target.company_id,
        "status": "active" if state.is_active else "inactive",
        "is_active": bool(state.is_active),
        "last_activity": (
            max((log.timestamp for log in target.activity_logs if log.timestamp), default=None).isoformat()
            if getattr(target, "activity_logs", None)
            else None
        ),
    }


@router.get("/admin/users")
def get_users(
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    users = user_service.get_all_users(db, company_id=user.company_id)
    serialized_users = [_serialize_user(db, u) for u in users]
    db.commit()
    return serialized_users


@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    created = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        role=_role_from_value(payload.role),
        company_id=user.company_id,
    )
    db.add(created)
    db.flush()
    get_or_create_account_state(db, created)
    db.commit()
    db.refresh(created)

    log_activity(
        db,
        user.user_id,
        "Created admin user",
        event_type="user",
        details=f"Created user {created.username}",
        company_id=user.company_id,
    )

    return _serialize_user(db, created)


@router.put("/admin/users/{user_id}")
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    target = db.query(User).filter(User.id == user_id, User.company_id == user.company_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username:
        proposed = payload.username.strip()
        duplicate = (
            db.query(User)
            .filter(User.username == proposed, User.id != user_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="Username already exists")
        target.username = proposed

    if payload.role:
        target.role = _role_from_value(payload.role)

    db.commit()
    db.refresh(target)

    log_activity(
        db,
        user.user_id,
        "Updated admin user",
        event_type="user",
        details=f"Updated user {target.username}",
        company_id=user.company_id,
    )

    return _serialize_user(db, target)


@router.put("/admin/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    target = db.query(User).filter(User.id == user_id, User.company_id == user.company_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_id == user_id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    set_user_active(db, target, payload.is_active)
    db.commit()
    db.refresh(target)

    next_status = "activated" if payload.is_active else "deactivated"
    log_activity(
        db,
        user.user_id,
        f"{next_status.title()} user account",
        event_type="user",
        details=f"{next_status.title()} user {target.username}",
        company_id=user.company_id,
    )

    return _serialize_user(db, target)


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    if user.user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    target = db.query(User).filter(User.id == user_id, User.company_id == user.company_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    username = target.username
    db.delete(target)
    db.commit()

    log_activity(
        db,
        user.user_id,
        "Deleted admin user",
        event_type="user",
        details=f"Deleted user {username}",
        company_id=user.company_id,
    )

    return {"deleted": user_id}

@router.get("/admin/monthly-usage")
async def admin_monthly_usage(
    month: str | None = Query(None, description="Month in YYYY-MM format"),
    user=Depends(require_role("admin")),
):

    try:

        if month:
            datetime.strptime(month, "%Y-%m")

        usage = get_monthly_usage(month)

        return {
            "month": month or datetime.now().strftime("%Y-%m"),
            "usage": usage
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
