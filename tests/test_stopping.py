import pytest

from backend.app.agent.state import InvestigationState, InvestigationStatus
from backend.app.agent.stopping import StoppingDecision, evaluate_stopping_policy


def test_continue_when_missing_evidence_remains():
    state = InvestigationState(
        iteration=2,
        missing_evidence=["error_logs", "trace_ids"],
        evidence_ids=["ev-1"],
    )
    decision = evaluate_stopping_policy(state, max_iterations=10)
    assert decision.should_stop is False
    assert "missing evidence remains" in decision.reason


def test_stop_when_sufficient_evidence_and_no_missing_evidence():
    state = InvestigationState(
        iteration=3,
        missing_evidence=[],
        evidence_ids=["ev-1", "ev-2"],
        observations=[{"summary": "Found memory leak"}],
    )
    decision = evaluate_stopping_policy(state, max_iterations=10)
    assert decision.should_stop is True
    assert "Sufficient evidence gathered" in decision.reason


def test_stop_on_failed_state():
    state = InvestigationState(
        status=InvestigationStatus.FAILED,
        missing_evidence=["logs"],
    )
    decision = evaluate_stopping_policy(state, max_iterations=10)
    assert decision.should_stop is True
    assert "FAILED" in decision.reason


def test_stop_on_iteration_limit():
    state = InvestigationState(
        iteration=10,
        missing_evidence=["logs"],
    )
    decision = evaluate_stopping_policy(state, max_iterations=10)
    assert decision.should_stop is True
    assert "maximum allowed iterations" in decision.reason
