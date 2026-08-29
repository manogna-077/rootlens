from typing import Any, Dict, List, Union, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class IncidentModel(BaseModel):
    id: str
    description: str
    signal: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

