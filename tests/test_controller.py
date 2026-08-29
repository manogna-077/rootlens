import pytest
from typing import List

from backend.app.agent.controller import InvestigationController
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.agent.planner import AgentAction
from backend.app.agent.state import InvestigationState, InvestigationStatus
from backend.app.agent.evaluator_bridge import bridge_evidence_evaluator
from backend.tools.executor import ToolExecutor as RealToolExecutor
from backend.tools.registry import ToolResult, ToolRegistry


def test_controller_iteration():
    controller = InvestigationController()

    state = InvestigationState(
        incident={"id": "inc-123", "service": "payment-api"},
        goal="Identify root cause of payment failure",
        missing_evidence=["logs"],
    )

    hypotheses = [
        Hypothesis(
            id="hyp-1",
            statement="Database connection timeout",
            status=HypothesisStatus.INVESTIGATING,
        )
    ]

    available_tools = [
        {"name": "fetch_logs", "required_params": ["service"]},
    ]

    def mock_executor(action: AgentAction) -> ToolResult:
        assert action.tool == "fetch_logs"
        return ToolResult(
            tool="fetch_logs",
            status="SUCCESS",
            evidence_ids=["ev-001", "ev-002"],
            observations=[{"summary": "Connection reset by peer"}],
            provenance=[],
        )

    updated_state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=mock_executor,
    )

    assert updated_state.iteration == 1
    assert updated_state.status == InvestigationStatus.RUNNING
    assert updated_state.selected_action is not None
    assert updated_state.selected_action["tool"] == "fetch_logs"
    assert updated_state.action_reason != ""
    assert updated_state.evidence_ids == ["ev-001", "ev-002"]
    assert updated_state.observations == [{"summary": "Connection reset by peer"}]
    assert len(updated_state.actions_taken) == 1
    assert len(updated_state.audit_events) == 1
    assert updated_state.audit_events[0]["iteration"] == 1
    assert updated_state.audit_events[0]["tool_result_status"] == "SUCCESS"


def test_controller_adaptive_behavior():
    controller = InvestigationController()

    state = InvestigationState(
        incident={"id": "inc-456", "service": "user-service"},
        goal="Determine root cause",
        missing_evidence=["deployments", "database_metrics"],
    )

    hypotheses = [
        Hypothesis(
            id="hyp-dep",
            statement="Recent deployment introduced defect",
            status=HypothesisStatus.INVESTIGATING,
        ),
        Hypothesis(
            id="hyp-db",
            statement="Database lock contention",
            status=HypothesisStatus.INVESTIGATING,
        ),
    ]

    available_tools = [
        {"name": "get_deployments", "required_params": ["service"]},
        {"name": "get_database_metrics", "required_params": ["service"]},
    ]

    # Iteration 1: initial missing evidence includes "deployments"
    def executor_iter1(action: AgentAction) -> ToolResult:
        assert action.tool == "get_deployments"
        return ToolResult(
            tool="get_deployments",
            status="SUCCESS",
            evidence_ids=["ev-dep-1"],
            observations=[{"summary": "No recent deployments found"}],
            provenance=[],
        )

    state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor_iter1,
    )

    assert state.iteration == 1
    assert state.selected_action is not None
    assert state.selected_action["tool"] == "get_deployments"

    # Update missing evidence based on results (deployments gathered, database_metrics remains)
    state.missing_evidence = ["database_metrics"]

    # Iteration 2: get_deployments already taken and deployments missing evidence resolved
    def executor_iter2(action: AgentAction) -> ToolResult:
        assert action.tool == "get_database_metrics"
        return ToolResult(
            tool="get_database_metrics",
            status="SUCCESS",
            evidence_ids=["ev-db-1"],
            observations=[{"summary": "High lock wait duration"}],
            provenance=[],
        )

    state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor_iter2,
    )

    assert state.iteration == 2
    assert state.selected_action is not None
    assert state.selected_action["tool"] == "get_database_metrics"
    assert "ev-dep-1" in state.evidence_ids
    assert "ev-db-1" in state.evidence_ids


def test_controller_with_real_tool_executor():
    controller = InvestigationController()
    real_executor = RealToolExecutor()

    state = InvestigationState(
        incident={"service": "api_gateway"},
        goal="Investigate api_gateway deployment issues",
        missing_evidence=["deployments"],
    )

    hypotheses = [
        Hypothesis(
            id="hyp-1",
            statement="Bad deployment",
            status=HypothesisStatus.INVESTIGATING,
        )
    ]

    available_tools = [
        {"name": "get_deployments", "required_params": ["service"]},
    ]

    updated_state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=real_executor,
    )

    assert updated_state.iteration == 1
    assert len(updated_state.actions_taken) == 1
    assert updated_state.selected_action["tool"] == "get_deployments"
    assert len(updated_state.evidence_ids) > 0
    assert len(updated_state.observations) > 0


def test_multi_step_investigation_loop_adaptive_actions():
    controller = InvestigationController()
    real_executor = RealToolExecutor()

    state = InvestigationState(
        incident={"service": "api_gateway"},
        goal="Determine root cause for api_gateway failures",
        missing_evidence=["deployments", "logs"],
    )

    hypotheses = [
        Hypothesis(
            id="hyp-1",
            statement="Deployment error or log errors",
            status=HypothesisStatus.INVESTIGATING,
        )
    ]

    available_tools = [
        {"name": "get_deployments", "required_params": ["service"]},
        {"name": "search_logs", "required_params": ["service"]},
    ]

    final_state = controller.run_investigation(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=real_executor,
        max_iterations=5,
    )

    # Proves multi-step loop executed multiple iterations with distinct actions
    assert final_state.iteration >= 2
    actions_taken_tools = [a["tool"] for a in final_state.actions_taken]
    assert "get_deployments" in actions_taken_tools
    assert "search_logs" in actions_taken_tools
    assert actions_taken_tools[0] != actions_taken_tools[1]
    assert len(final_state.evidence_ids) > 0
    assert len(final_state.observations) > 0


def test_controller_calls_injected_evidence_evaluator():
    controller = InvestigationController()

    state = InvestigationState(
        incident={"service": "user-service"},
        missing_evidence=["logs"],
    )
    hypotheses = [
        Hypothesis(id="hyp-1", statement="Service crash", status=HypothesisStatus.INVESTIGATING)
    ]
    available_tools = [{"name": "fetch_logs", "required_params": ["service"]}]

    evaluator_called = []

    def mock_evaluator(tool_result: ToolResult, hyps: List[Hypothesis]) -> None:
        evaluator_called.append((tool_result.tool, len(hyps)))

    def mock_executor(action: AgentAction) -> ToolResult:
        return ToolResult(
            tool="fetch_logs",
            status="SUCCESS",
            evidence_ids=["ev-1"],
            observations=[{"summary": "Fatal exception"}],
            provenance=[],
        )

    updated_state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=mock_executor,
        evidence_evaluator=mock_evaluator,
    )

    assert len(evaluator_called) == 1
    assert evaluator_called[0] == ("fetch_logs", 1)


def test_evidence_evaluator_bridge_integration():
    controller = InvestigationController()
    real_executor = RealToolExecutor()

    state = InvestigationState(
        incident={"service": "api_gateway"},
        missing_evidence=["deployments", "logs"],
    )

    hypotheses = [
        Hypothesis(
            id="hyp-dep",
            statement="api_gateway configuration deployment changed failure",
            status=HypothesisStatus.INVESTIGATING,
        ),
        Hypothesis(
            id="hyp-db",
            statement="database lock timeout",
            status=HypothesisStatus.INVESTIGATING,
        ),
    ]

    available_tools = [
        {"name": "get_deployments", "required_params": ["service"]},
        {"name": "search_logs", "required_params": ["service"]},
    ]

    # Run investigation passing the evaluator_bridge
    final_state = controller.run_investigation(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=real_executor,
        evidence_evaluator=bridge_evidence_evaluator,
        max_iterations=3,
    )

    # Verify that evidence evaluation updated hypothesis state
    hyp_dep = next(h for h in hypotheses if h.id == "hyp-dep")
    assert len(hyp_dep.supporting_evidence_ids) > 0 or len(hyp_dep.contradicting_evidence_ids) > 0
    assert hyp_dep.status in (HypothesisStatus.SUPPORTED, HypothesisStatus.WEAKENED)
    assert hyp_dep.reasoning != ""
