from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.agent.state import InvestigationState


class ReflectionOutput(BaseModel):
    learned: List[str] = Field(default_factory=list)
    strengthened: List[str] = Field(default_factory=list)
    weakened: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    next_action: Optional[Dict[str, Any]] = None
    should_stop: bool = False


def apply_reflection_to_state(
    reflection: ReflectionOutput,
    state: InvestigationState,
) -> InvestigationState:
    state.missing_evidence = list(reflection.missing_evidence)

    if reflection.next_action:
        state.selected_action = reflection.next_action
        reason = reflection.next_action.get("reason", "")
        if reason:
            state.action_reason = reason

    for item in reflection.learned:
        obs_entry = {"source": "reflection", "summary": item}
        if obs_entry not in state.observations:
            state.observations.append(obs_entry)

    audit_entry = {
        "event": "reflection_applied",
        "iteration": state.iteration,
        "learned_count": len(reflection.learned),
        "strengthened": reflection.strengthened,
        "weakened": reflection.weakened,
        "contradictions": reflection.contradictions,
        "missing_evidence_count": len(reflection.missing_evidence),
        "should_stop": reflection.should_stop,
    }
    state.audit_events.append(audit_entry)

    return state
