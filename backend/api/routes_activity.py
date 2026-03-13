from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.rbac import require_roles
from backend.database.database import SessionLocal
from backend.services.activity_service import get_recent_activity_logs

router = APIRouter(tags=["Activity"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/activity-logs")
def activity_logs(
    limit: int = Query(100, ge=1, le=500),
    user=Depends(require_roles("admin", "manager")),
    db: Session = Depends(get_db),
):
    return get_recent_activity_logs(db, company_id=user.company_id, limit=limit)