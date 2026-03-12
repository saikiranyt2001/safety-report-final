# Hazard request/response schemas

# Add Pydantic models for hazard data, detection, etc.
from pydantic import BaseModel


class HazardRequest(BaseModel):
    site_type: str


class HazardResponse(BaseModel):
    hazard: str
    category: str