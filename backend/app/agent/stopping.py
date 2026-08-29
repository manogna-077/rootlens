from pydantic import BaseModel
from backend.app.agent.state import InvestigationState, InvestigationStatus

DEFAULT_MAX_ITERATIONS = 10


class StoppingDecision(BaseModel):
    should_stop: bool
    reason: str


def evaluate_stopping_policy(
    state: InvestigationState,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> StoppingDecision:
    if state.status == InvestigationStatus.FAILED:
        return StoppingDecision(
            should_stop=True,
            reason="Investigation status is FAILED",
        )

    if state.iteration >= max_iterations:
        return StoppingDecision(
            should_stop=True,
            reason=f"Reached maximum allowed iterations ({max_iterations})",
        )

    if state.missing_evidence:
        return StoppingDecision(
            should_stop=False,
            reason=f"Investigation should continue; missing evidence remains: {', '.join(state.missing_evidence)}",
        )

    if len(state.evidence_ids) > 0 or len(state.observations) > 0:
        return StoppingDecision(
            should_stop=True,
            reason="Sufficient evidence gathered and no critical missing evidence remains",
        )

    return StoppingDecision(
        should_stop=False,
        reason="Investigation in progress; awaiting initial evidence collection",
    )
