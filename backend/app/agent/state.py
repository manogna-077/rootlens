from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PASS = "PASS"
    FAIL = "FAIL"


class InvestigationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    FAILED = "FAILED"


class InvestigationState(BaseModel):
    incident: Dict[str, Any] = Field(default_factory=dict)
    goal: str = ""
    time_window: Dict[str, Any] = Field(default_factory=dict)
    iteration: int = 0
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    candidate_actions: List[Dict[str, Any]] = Field(default_factory=list)
    selected_action: Optional[Dict[str, Any]] = None
    action_reason: str = ""
    evidence_score: Optional[float] = None
    verification_status: VerificationStatus = VerificationStatus.NOT_STARTED
    status: InvestigationStatus = InvestigationStatus.NOT_STARTED
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
