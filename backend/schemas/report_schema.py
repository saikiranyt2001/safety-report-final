# Report request/response schemas

# Add Pydantic models for report generation, history, etc.
from pydantic import BaseModel
from datetime import datetime


class ReportCreate(BaseModel):
    project_id: int
    site_type: str


class ReportResponse(BaseModel):
    id: int
    project_id: int
    risk_level: str
    created_at: datetime