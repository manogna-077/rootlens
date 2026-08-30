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


def test_positional_missing_evidence_priority():
    hyp = Hypothesis(id="hyp-1", statement="Investigating outage", status=HypothesisStatus.GENERATED)
    missing_list = ["primary_evidence", "secondary_evidence", "tertiary_evidence"]

    act_primary = AgentAction(tool="tool_a", target_hypotheses=["hyp-1"], missing_evidence_addressed=["primary_evidence"])
    act_tertiary = AgentAction(tool="tool_c", target_hypotheses=["hyp-1"], missing_evidence_addressed=["tertiary_evidence"])

    score_p = calculate_diagnostic_usefulness(act_primary, [hyp], missing_list)
    score_t = calculate_diagnostic_usefulness(act_tertiary, [hyp], missing_list)

    assert score_p > score_t


def test_domain_alignment_bonus():
    hyp = Hypothesis(id="hyp-1", statement="Database lock contention and timeout", status=HypothesisStatus.GENERATED)
    act_db = AgentAction(tool="query_metrics", target_hypotheses=["hyp-1"], missing_evidence_addressed=["metrics"])
    act_generic = AgentAction(tool="unknown_tool", target_hypotheses=["hyp-1"], missing_evidence_addressed=["metrics"])

    score_db = calculate_diagnostic_usefulness(act_db, [hyp], ["metrics"], context_text="database timeout saturation")
    score_gen = calculate_diagnostic_usefulness(act_generic, [hyp], ["metrics"], context_text="database timeout saturation")

    assert score_db > score_gen


def test_scenario_a_vs_scenario_b_differentiation():
    from backend.app.main import run_incident_investigation
    state_a = run_incident_investigation("scenario_a")
    state_b = run_incident_investigation("scenario_b")

    first_action_a = state_a.actions_taken[0]["tool"]
    first_action_b = state_b.actions_taken[0]["tool"]

    assert first_action_a == "get_deployments"
    assert first_action_b == "query_metrics"
    assert first_action_a != first_action_b


def test_no_scenario_hardcoding_in_planner():
    import inspect
    import backend.app.agent.planner as planner_mod
    source = inspect.getsource(planner_mod)

    assert "scenario_a" not in source.lower()
    assert "scenario_b" not in source.lower()
    assert "scenario_c" not in source.lower()
    assert "scenario_d" not in source.lower()
