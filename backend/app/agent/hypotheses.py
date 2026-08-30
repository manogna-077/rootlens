from enum import Enum
from typing import Any, Dict, List, Optional
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


def build_initial_hypotheses(incident_data: Dict[str, Any]) -> List[Hypothesis]:
    inc_id = str(incident_data.get("id", "inc"))
    desc = str(incident_data.get("description", "") or "")
    signal = str(incident_data.get("signal", "") or "")
    combined_text = f"{desc} {signal}".lower()

    # 1. Direct explicit candidate hypotheses in incident data
    if "hypotheses" in incident_data and isinstance(incident_data["hypotheses"], list):
        results = []
        for idx, item in enumerate(incident_data["hypotheses"]):
            if isinstance(item, dict):
                results.append(
                    Hypothesis(
                        id=item.get("id", f"hyp-{inc_id}-{idx + 1}"),
                        statement=item.get("statement", f"Hypothesis {idx + 1}"),
                        disconfirming_condition=item.get("disconfirming_condition"),
                        status=HypothesisStatus.GENERATED,
                    )
                )
            elif isinstance(item, str):
                results.append(
                    Hypothesis(
                        id=f"hyp-{inc_id}-{idx + 1}",
                        statement=item,
                        status=HypothesisStatus.GENERATED,
                    )
                )
        if results:
            return results

    # 2. General detection for ambiguous / multi-cause signals
    ambiguity_keywords = ["ambiguous", "insufficient", "multiple", "two causes", "unclear", "competing", "plausible"]
    is_ambiguous = any(kw in combined_text for kw in ambiguity_keywords)

    if is_ambiguous:
        return [
            Hypothesis(
                id=f"hyp-{inc_id}-1",
                statement="Recent deployment software regression or configuration change",
                disconfirming_condition="no recent deployments or version changes",
                status=HypothesisStatus.GENERATED,
            ),
            Hypothesis(
                id=f"hyp-{inc_id}-2",
                statement="Database or cache lookup failure or backend service error",
                disconfirming_condition="healthy database and cache token validation logs",
                status=HypothesisStatus.GENERATED,
            ),
        ]

    # 3. Domain-based single hypothesis with disconfirming condition
    if "database" in combined_text or "db" in combined_text or "lock" in combined_text or "saturation" in combined_text:
        disc = "healthy database lock wait time and normal connection count"
        statement_str = "Database resource exhaustion, lock contention, or query timeouts"
    elif "dependency" in combined_text or "external" in combined_text or "provider" in combined_text:
        disc = "all third party dependencies report normal status and response latency"
        statement_str = "External third-party dependency outage or API performance degradation"
    elif "deploy" in combined_text or "release" in combined_text:
        disc = "no deployment changes or version modifications"
        statement_str = "Recent deployment software regression or configuration change"
    else:
        disc = "telemetry shows no abnormal metrics or errors"
        statement_str = f"Root cause related to {desc or inc_id}"

    return [
        Hypothesis(
            id=f"hyp-{inc_id}-1",
            statement=statement_str,
            disconfirming_condition=disc,
            status=HypothesisStatus.GENERATED,
        )
    ]
