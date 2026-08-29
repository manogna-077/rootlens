import pytest
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.agent.planner import AgentAction, Planner, calculate_diagnostic_usefulness
from backend.app.agent.state import InvestigationState


def test_agent_action_contract():
    action = AgentAction(
        tool="fetch_logs",
        arguments={"service": "auth-service"},
        reason="Check logs for errors",
        target_hypotheses=["hyp-1"],
        missing_evidence_addressed=["error_logs"],
    )
    assert action.tool == "fetch_logs"
    assert action.arguments == {"service": "auth-service"}
    assert action.reason == "Check logs for errors"
    assert action.target_hypotheses == ["hyp-1"]
    assert action.missing_evidence_addressed == ["error_logs"]


def test_planner_selection_differs_by_investigation_state():
    planner = Planner()
    available_tools = [
        {"name": "logs", "required_params": ["service"]},
        {"name": "metrics", "required_params": ["service"]},
    ]

    # State 1: Missing 'logs' evidence, hypothesis under INVESTIGATING
    hyp1 = Hypothesis(id="hyp-1", statement="High memory usage", status=HypothesisStatus.INVESTIGATING)
    state1 = InvestigationState(
        incident={"service": "payment-api"},
        actions_taken=[],
    )
    candidates1, selected1 = planner.plan(
        state=state1,
        hypotheses=[hyp1],
        missing_evidence=["logs"],
        available_tools=available_tools,
    )
    assert selected1 is not None
    assert selected1.tool == "logs"
    assert selected1.arguments == {"service": "payment-api"}

    # State 2: 'logs' action already taken in state 2, so planner selects 'metrics' next
    state2 = InvestigationState(
        incident={"service": "payment-api"},
        actions_taken=[{"tool": "logs", "arguments": {"service": "payment-api"}}],
    )
    candidates2, selected2 = planner.plan(
        state=state2,
        hypotheses=[hyp1],
        missing_evidence=["logs"],
        available_tools=available_tools,
    )
    assert selected2 is not None
    assert selected2.tool == "metrics"


def test_diagnostic_usefulness_ranking():
    hyp = Hypothesis(id="hyp-1", statement="CPU Spike", status=HypothesisStatus.INVESTIGATING)
    
    act_high = AgentAction(
        tool="metrics",
        target_hypotheses=["hyp-1"],
        missing_evidence_addressed=["metrics"],
    )
    act_low = AgentAction(
        tool="traces",
        target_hypotheses=[],
        missing_evidence_addressed=[],
    )

    score_high = calculate_diagnostic_usefulness(act_high, [hyp], ["metrics"])
    score_low = calculate_diagnostic_usefulness(act_low, [hyp], ["metrics"])

    assert score_high > score_low
