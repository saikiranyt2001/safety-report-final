from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.rbac import require_roles
from backend.services import compliance_service

router = APIRouter(tags=["AI Tools"])


class IncidentPredictionPayload(BaseModel):
    environment: str
    workers: int
    violations: int


class ComplianceAnalysisPayload(BaseModel):
    text: str


@router.post("/incident-prediction")
def incident_prediction(
    payload: IncidentPredictionPayload,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    risk_score = min(100, max(0, payload.violations * 18 + payload.workers))

    environment = payload.environment.strip().lower()
    if "construction" in environment:
        risk_score = min(100, risk_score + 15)
    elif "factory" in environment:
        risk_score = min(100, risk_score + 10)

    if risk_score >= 80:
        risk_level = "HIGH"
    elif risk_score >= 50:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    recommended_actions = [
        "Increase PPE monitoring",
        "Conduct focused safety training",
        "Inspect the highest-risk work zones",
    ]
    if payload.violations == 0:
        recommended_actions = [
            "Continue routine inspections",
            "Refresh toolbox talks weekly",
            "Monitor environmental changes on site",
        ]

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "recommended_actions": recommended_actions,
    }


@router.post("/compliance/analyze-text")
def compliance_analyze_text(
    payload: ComplianceAnalysisPayload,
    _user=Depends(require_roles("admin", "manager", "worker")),
):
    text = payload.text.strip().lower()
    suggestions = compliance_service.suggested_rules(text[:80] if text else "safety")

    findings = []
    if "helmet" not in text and "ppe" not in text:
        findings.append("PPE requirements are not clearly documented.")
    if "fall" in text or "ladder" in text or "scaffold" in text:
        findings.append("Fall protection controls should be verified.")
    if "electric" in text or "wire" in text or "panel" in text:
        findings.append("Electrical isolation and inspection steps should be confirmed.")

    if not findings:
        findings.append("No obvious compliance gaps were detected from the supplied text.")

    return {
        "status": "Review Required" if len(findings) > 1 else "Looks Good",
        "findings": findings,
        "suggested_rules": suggestions[:5],
    }
