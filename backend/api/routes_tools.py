import json
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.ai_client import chat_completion
from backend.core.rbac import require_roles
from backend.services import compliance_service

router = APIRouter(tags=["AI Tools"])


class IncidentPredictionPayload(BaseModel):
    environment: str
    workers: int
    violations: int
    shift_hours: int = 8
    fatigue_level: str = "medium"
    ppe_compliance: int = 75
    high_risk_task: str = "general operations"
    weather: str = "indoor"


class ComplianceAnalysisPayload(BaseModel):
    text: str


def _base_incident_prediction(payload: IncidentPredictionPayload):
    risk_score = min(100, max(0, payload.violations * 18 + payload.workers))

    environment = payload.environment.strip().lower()
    if "construction" in environment:
        risk_score = min(100, risk_score + 15)
    elif "factory" in environment:
        risk_score = min(100, risk_score + 10)
    elif "warehouse" in environment:
        risk_score = min(100, risk_score + 8)

    if payload.shift_hours >= 12:
        risk_score = min(100, risk_score + 15)
    elif payload.shift_hours >= 10:
        risk_score = min(100, risk_score + 8)

    fatigue = payload.fatigue_level.strip().lower()
    if fatigue == "high":
        risk_score = min(100, risk_score + 15)
    elif fatigue == "medium":
        risk_score = min(100, risk_score + 7)

    if payload.ppe_compliance < 60:
        risk_score = min(100, risk_score + 18)
    elif payload.ppe_compliance < 85:
        risk_score = min(100, risk_score + 9)

    task = payload.high_risk_task.strip().lower()
    if any(token in task for token in ["welding", "electrical", "height", "confined", "crane", "forklift"]):
        risk_score = min(100, risk_score + 12)

    weather = payload.weather.strip().lower()
    if any(token in weather for token in ["rain", "storm", "heat", "wind"]):
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
    if fatigue == "high":
        recommended_actions.append("Rotate crews and add fatigue management breaks")
    if payload.ppe_compliance < 85:
        recommended_actions.append("Run an immediate PPE compliance check")
    if any(token in task for token in ["electrical", "confined", "height"]):
        recommended_actions.append("Assign a supervisor for the highest-risk task window")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "recommended_actions": recommended_actions[:5],
        "summary": (
            f"Rule-based prediction for {payload.environment}: {risk_level} risk with "
            f"{payload.workers} workers, {payload.violations} violations, and PPE compliance at {payload.ppe_compliance}%."
        ),
        "engine": "rules",
    }


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _ai_incident_prediction(payload: IncidentPredictionPayload, fallback: dict) -> dict | None:
    prompt = f"""
You are an industrial safety risk analyst.
Given the workplace conditions below, predict incident risk.
Return only valid JSON with this schema:
{{
  "risk_level": "LOW|MEDIUM|HIGH",
  "risk_score": 0,
  "summary": "short paragraph",
  "recommended_actions": ["action 1", "action 2", "action 3"]
}}

Conditions:
- Environment: {payload.environment}
- Workers on shift: {payload.workers}
- Safety violations: {payload.violations}
- Shift hours: {payload.shift_hours}
- Fatigue level: {payload.fatigue_level}
- PPE compliance: {payload.ppe_compliance}
- Highest risk task: {payload.high_risk_task}
- Weather/site condition: {payload.weather}

Use this fallback score as a reference point, but adjust if needed:
- Fallback risk level: {fallback["risk_level"]}
- Fallback risk score: {fallback["risk_score"]}
"""

    try:
        response = chat_completion(prompt, max_tokens=260)
    except Exception:
        return None

    parsed = _extract_json_object(response)
    if not parsed:
        return None

    risk_level = str(parsed.get("risk_level", fallback["risk_level"])).upper()
    if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
        risk_level = fallback["risk_level"]

    try:
        risk_score = int(parsed.get("risk_score", fallback["risk_score"]))
    except (TypeError, ValueError):
        risk_score = fallback["risk_score"]

    recommended_actions = parsed.get("recommended_actions", fallback["recommended_actions"])
    if not isinstance(recommended_actions, list) or not recommended_actions:
        recommended_actions = fallback["recommended_actions"]

    summary = str(parsed.get("summary", fallback["summary"])).strip() or fallback["summary"]

    return {
        "risk_level": risk_level,
        "risk_score": max(0, min(100, risk_score)),
        "recommended_actions": [str(item) for item in recommended_actions[:5]],
        "summary": summary,
        "engine": "ai",
    }


@router.post("/incident-prediction")
def incident_prediction(
    payload: IncidentPredictionPayload,
):
    fallback = _base_incident_prediction(payload)
    ai_result = _ai_incident_prediction(payload, fallback)
    return ai_result or fallback


@router.post("/compliance/analyze-text")
def compliance_analyze_text(
    payload: ComplianceAnalysisPayload,
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
