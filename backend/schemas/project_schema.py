# Project request/response schemas

# Add Pydantic models for project creation, management, etc.
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str