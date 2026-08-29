import pytest
from backend.app.agent.state import (
    InvestigationState,
    VerificationStatus,
    InvestigationStatus,
)


def test_investigation_state_defaults():
    state = InvestigationState()

    assert state.incident == {}
    assert state.goal == ""
    assert state.time_window == {}
    assert state.iteration == 0
    assert state.actions_taken == []
    assert state.evidence_ids == []
    assert state.hypotheses == []
    assert state.observations == []
    assert state.missing_evidence == []
    assert state.candidate_actions == []
    assert state.selected_action is None
    assert state.action_reason == ""
    assert state.evidence_score is None
    assert state.verification_status == VerificationStatus.NOT_STARTED
    assert state.status == InvestigationStatus.NOT_STARTED
    assert state.audit_events == []


def test_investigation_state_custom_values():
    state = InvestigationState(
        incident={"id": "inc-123"},
        goal="Determine root cause of high latency",
        iteration=1,
        selected_action={"tool": "query_logs", "arguments": {}},
        evidence_score=0.85,
        verification_status=VerificationStatus.PASS,
        status=InvestigationStatus.RUNNING,
    )

    assert state.incident["id"] == "inc-123"
    assert state.goal == "Determine root cause of high latency"
    assert state.iteration == 1
    assert state.selected_action == {"tool": "query_logs", "arguments": {}}
    assert state.evidence_score == 0.85
    assert state.verification_status == VerificationStatus.PASS
    assert state.status == InvestigationStatus.RUNNING
