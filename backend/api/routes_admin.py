#done
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from ..services.usage_tracker import get_monthly_usage

router = APIRouter(tags=["Admin"])

@router.get("/admin/monthly-usage")
async def admin_monthly_usage(
    month: str | None = Query(None, description="Month in YYYY-MM format")
):
    try:
        usage = get_monthly_usage(month)
        return {
            "month": month or datetime.now().strftime("%Y-%m"),
            "usage": usage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))