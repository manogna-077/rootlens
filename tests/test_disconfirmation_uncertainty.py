import pytest
import inspect
from backend.app.agent.controller import InvestigationController
from backend.app.agent.evaluator_bridge import bridge_evidence_evaluator
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus, build_initial_hypotheses
from backend.app.agent.state import InvestigationState, InvestigationStatus
from backend.app.agent.stopping import evaluate_stopping_policy
from backend.app.main import run_incident_investigation, get_incident_report
from backend.app.reasoning.disconfirmation import DisconfirmationEvaluator
from backend.app.reasoning.evidence_evaluator import EvidenceInput, HypothesisInput
from backend.app.reasoning.verifier import Verifier, VerificationContext, VerificationStatus
from backend.tools.executor import ToolExecutor


def test_empty_missing_evidence_without_confirmed_hypothesis_yields_insufficient_evidence():
    controller = InvestigationController()
    state = InvestigationState(
        incident={"id": "test_ambiguous", "description": "Unresolved issue", "signal": "two causes remain plausible"},
        missing_evidence=["logs"],
    )
    hypotheses = [
        Hypothesis(id="hyp-1", statement="Hypothesis 1", status=HypothesisStatus.GENERATED),
        Hypothesis(id="hyp-2", statement="Hypothesis 2", status=HypothesisStatus.GENERATED),
    ]
    available_tools = [{"name": "search_logs", "required_params": []}]
    executor = ToolExecutor()

    final_state = controller.run_investigation(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor,
        evidence_evaluator=bridge_evidence_evaluator,
    )

    assert final_state.status == InvestigationStatus.INSUFFICIENT_EVIDENCE


def test_confirmed_hypothesis_yields_completed_status():
    controller = InvestigationController()
    state = InvestigationState(
        incident={"id": "test_confirmed", "description": "Deployment regression", "signal": "release error"},
        missing_evidence=["deployments"],
    )
    hypotheses = [
        Hypothesis(
            id="hyp-1",
            statement="Recent deployment software regression or configuration change",
            status=HypothesisStatus.GENERATED,
            supporting_evidence_ids=["ev_dep_001", "ev_log_001"],
        )
    ]
    # Manually promote to CONFIRMED
    hypotheses[0].status = HypothesisStatus.CONFIRMED

    available_tools = [{"name": "get_deployments", "required_params": []}]
    executor = ToolExecutor()

    final_state = controller.run_investigation(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor,
        evidence_evaluator=bridge_evidence_evaluator,
    )

    assert final_state.status == InvestigationStatus.COMPLETED


def test_multiple_candidate_hypotheses_initialization():
    incident = {"id": "scenario_d", "description": "Insufficient evidence / ambiguous case", "signal": "two causes remain plausible"}
    hypotheses = build_initial_hypotheses(incident)
    assert len(hypotheses) >= 2
    assert hypotheses[0].disconfirming_condition is not None
    assert hypotheses[1].disconfirming_condition is not None


def test_disconfirming_evidence_weakens_hypothesis():
    ev = EvidenceInput(id="ev-1", observation="healthy database lock wait time and normal connection count")
    hyp = HypothesisInput(id="hyp-1", statement="Database lock timeout", disconfirming_condition="healthy database lock wait time")

    disc_res = DisconfirmationEvaluator.evaluate(ev, hyp)
    assert disc_res.disconfirms is True


def test_lack_of_support_does_not_equal_disconfirmation():
    ev = EvidenceInput(id="ev-2", observation="routine health check ping successful")
    hyp = HypothesisInput(id="hyp-1", statement="Database lock timeout", disconfirming_condition="unrelated_term_xxx")

    disc_res = DisconfirmationEvaluator.evaluate(ev, hyp)
    assert disc_res.disconfirms is False


def test_valid_insufficient_evidence_report_passes_verifier():
    context = VerificationContext(
        evidence_items=[{"id": "ev-1", "observation": "generic log"}],
        hypotheses=[
            {"id": "hyp-1", "statement": "Hypothesis 1", "status": "SUPPORTED", "supporting_evidence_ids": ["ev-1"]},
            {"id": "hyp-2", "statement": "Hypothesis 2", "status": "INVESTIGATING"},
        ],
    )
    result = Verifier.verify(context)
    assert result.status == VerificationStatus.PASS


def test_unsupported_rca_fails_verifier():
    context = VerificationContext(
        evidence_items=[],
        hypotheses=[
            {"id": "hyp-1", "statement": "Fake Root Cause", "status": "CONFIRMED", "supporting_evidence_ids": []}
        ],
    )
    result = Verifier.verify(context)
    assert result.status == VerificationStatus.FAIL
    assert len(result.missing_support) > 0


def test_scenario_d_returns_insufficient_evidence():
    state = run_incident_investigation("scenario_d")
    report = get_incident_report("scenario_d")

    assert state.status == InvestigationStatus.INSUFFICIENT_EVIDENCE
    assert report["verification"]["status"] == "PASS"


def test_scenarios_a_b_c_retain_intended_outcomes():
    state_a = run_incident_investigation("scenario_a")
    state_b = run_incident_investigation("scenario_b")
    state_c = run_incident_investigation("scenario_c")

    assert state_a.status == InvestigationStatus.COMPLETED
    assert state_b.status == InvestigationStatus.COMPLETED
    assert state_c.status == InvestigationStatus.COMPLETED


def test_no_scenario_specific_production_logic():
    import backend.app.agent.controller as ctrl_mod
    import backend.app.agent.hypotheses as hyp_mod
    import backend.app.agent.stopping as stop_mod

    for mod in (ctrl_mod, hyp_mod, stop_mod):
        src = inspect.getsource(mod).lower()
        assert "scenario_a" not in src
        assert "scenario_b" not in src
        assert "scenario_c" not in src
        assert "scenario_d" not in src
