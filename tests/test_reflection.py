import pytest

from backend.app.agent.reflection import ReflectionOutput, apply_reflection_to_state
from backend.app.agent.state import InvestigationState


def test_reflection_output_structure():
    reflection = ReflectionOutput(
        learned=["Database pool size exhausted at 10:15"],
        strengthened=["hyp-1"],
        weakened=["hyp-2"],
        contradictions=["No network latency spike found"],
        missing_evidence=["slow_query_logs"],
        next_action={"tool": "get_slow_query_logs", "arguments": {"service": "db"}},
        should_stop=False,
    )

    assert reflection.learned == ["Database pool size exhausted at 10:15"]
    assert reflection.strengthened == ["hyp-1"]
    assert reflection.weakened == ["hyp-2"]
    assert reflection.contradictions == ["No network latency spike found"]
    assert reflection.missing_evidence == ["slow_query_logs"]
    assert reflection.next_action == {"tool": "get_slow_query_logs", "arguments": {"service": "db"}}
    assert reflection.should_stop is False


def test_apply_reflection_to_state():
    state = InvestigationState(
        incident={"id": "inc-789"},
        missing_evidence=["initial_logs"],
        observations=[],
        evidence_ids=["ev-1"],
    )

    reflection = ReflectionOutput(
        learned=["Connection pool saturated"],
        strengthened=["hyp-1"],
        weakened=[],
        contradictions=[],
        missing_evidence=["connection_pool_metrics"],
        next_action={
            "tool": "get_pool_metrics",
            "arguments": {"service": "db"},
            "reason": "Verify connection pool usage",
        },
        should_stop=False,
    )

    updated_state = apply_reflection_to_state(reflection, state)

    # Missing evidence updated
    assert updated_state.missing_evidence == ["connection_pool_metrics"]

    # Next action recorded
    assert updated_state.selected_action == {
        "tool": "get_pool_metrics",
        "arguments": {"service": "db"},
        "reason": "Verify connection pool usage",
    }
    assert updated_state.action_reason == "Verify connection pool usage"

    # Learned added to observations, no evidence invented
    assert updated_state.evidence_ids == ["ev-1"]
    assert len(updated_state.observations) == 1
    assert updated_state.observations[0]["summary"] == "Connection pool saturated"

    # Audit event recorded
    assert len(updated_state.audit_events) == 1
    assert updated_state.audit_events[0]["event"] == "reflection_applied"
