# Risk request/response schemas

# Add Pydantic models for risk assessment, heatmap, etc.
from pydantic import BaseModel


class RiskRequest(BaseModel):
    likelihood: int
    severity: int


class RiskResponse(BaseModel):
    risk_score: int
    risk_level: str