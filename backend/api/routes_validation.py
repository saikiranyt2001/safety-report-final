#done
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from ..agents.validation_agent import ValidationAgent
from backend.core.rbac import require_roles

router = APIRouter(tags=["Validation"])


class ValidationRequest(BaseModel):
    report_text: str
    hazard_list: List[str]
    regulation_list: List[str]


class ValidationResponse(BaseModel):
    issues: List[str]


@router.post("/validate-report", response_model=ValidationResponse)
async def validate_report(
    payload: ValidationRequest,
    _user=Depends(require_roles("admin", "manager")),
):
    try:
        agent = ValidationAgent(
            hazard_list=payload.hazard_list,
            regulation_list=payload.regulation_list
        )

        issues = agent.validate_report(payload.report_text)

        return {"issues": issues}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )