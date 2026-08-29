from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class HypothesisStatus(str, Enum):
    GENERATED = "GENERATED"
    INVESTIGATING = "INVESTIGATING"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Hypothesis(BaseModel):
    id: str
    statement: str
    status: HypothesisStatus = HypothesisStatus.GENERATED
    score: float = 0.0
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    disconfirming_condition: Optional[str] = None
    reasoning: str = ""

    def add_supporting_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.supporting_evidence_ids:
            self.supporting_evidence_ids.append(evidence_id)

    def add_contradicting_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.contradicting_evidence_ids:
            self.contradicting_evidence_ids.append(evidence_id)

    def set_missing_evidence(self, missing_items: List[str]) -> None:
        self.missing_evidence = list(missing_items)

    def update_assessment(
        self,
        status: Optional[HypothesisStatus] = None,
        score: Optional[float] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        if status is not None:
            self.status = status
        if score is not None:
            self.score = score
        if reasoning is not None:
            self.reasoning = reasoning
