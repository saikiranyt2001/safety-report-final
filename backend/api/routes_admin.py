from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from ..services.usage_tracker import get_monthly_usage
from backend.core.dependencies import require_role
from backend.core.dependencies import get_database
from backend.services import user_service
from sqlalchemy.orm import Session

router = APIRouter(tags=["Admin"])


@router.get("/admin/users")
def get_users(
    user=Depends(require_role("admin")),
    db: Session = Depends(get_database),
):
    users = user_service.get_all_users(db, company_id=user.company_id)
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "company_id": u.company_id,
        }
        for u in users
    ]

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