from typing import Any, Dict, List, Union, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class IncidentModel(BaseModel):
    id: str
    description: str
    signal: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceModel(BaseModel):
    id: str
    incident_id: str
    timestamp: str
    source: str
    event_type: str
    service: str
    version: Optional[str] = None
    observation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool
    approver: Optional[str] = "admin"
    comments: Optional[str] = ""


class ApprovalResponse(BaseModel):
    incident_id: str
    approved: bool
    status: str
    message: str


