from pydantic import BaseModel
from typing import Dict, Any

class PipelineRequest(BaseModel):
    site_type: str
    site_data: Dict[str, Any]
