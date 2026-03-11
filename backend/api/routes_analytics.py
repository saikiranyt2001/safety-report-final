#done
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.models import Report
from backend.database.database import SessionLocal
from sqlalchemy import func
from fastapi.security import HTTPBearer


router = APIRouter(tags=["Dashboard"])

security = HTTPBearer()

from fastapi import HTTPException, status

def verify_token(token=Depends(security)):
    # Example validation: replace with real logic
    if not token or not token.credentials or token.credentials != "expected_token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard/metrics")
async def dashboard_metrics(
    token=Depends(verify_token),
    db: Session = Depends(get_db)
):
    results = (
        db.query(Report.severity, func.count(Report.id))
        .group_by(Report.severity)
        .all()
    )

    metrics = {severity: count for severity, count in results}

    return {"metrics": metrics}
