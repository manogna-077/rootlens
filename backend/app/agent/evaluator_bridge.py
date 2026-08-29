from typing import List
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.reasoning.evidence_evaluator import (
    AssessmentType,
    EvidenceEvaluator,
    EvidenceInput,
    HypothesisInput,
)
from backend.tools.registry import ToolResult


def bridge_evidence_evaluator(tool_result: ToolResult, hypotheses: List[Hypothesis]) -> None:
    """
    Person 1 ↔ Person 4 Evidence Evaluator Bridge.
    Converts ToolResult observations into evidence inputs, evaluates them against active hypotheses,
    updates supporting/contradicting evidence lists, hypothesis reasoning, and status.
    """
    if not tool_result or not hypotheses:
        return

    evidence_ids = getattr(tool_result, "evidence_ids", [])
    observations = getattr(tool_result, "observations", [])

    # If no explicit observations exist, create a summary observation from tool result status
    obs_list = observations if observations else [{"summary": f"Tool {tool_result.tool} returned status {tool_result.status}"}]

    for idx, obs_dict in enumerate(obs_list):
        ev_id = evidence_ids[idx] if idx < len(evidence_ids) else f"{tool_result.tool}_ev_{idx + 1}"
        if isinstance(obs_dict, dict):
            obs_text = obs_dict.get("summary") or obs_dict.get("observation") or str(obs_dict)
            service_val = obs_dict.get("service")
        else:
            obs_text = str(obs_dict)
            service_val = None

        ev_input = EvidenceInput(
            id=ev_id,
            service=service_val,
            observation=obs_text,
        )

        for hyp in hypotheses:
            hyp_input = HypothesisInput(
                id=hyp.id,
                statement=hyp.statement,
                disconfirming_condition=hyp.disconfirming_condition,
            )

            assessment = EvidenceEvaluator.evaluate(ev_input, hyp_input)

            if assessment.assessment == AssessmentType.SUPPORTS:
                hyp.add_supporting_evidence(ev_id)
                new_status = HypothesisStatus.SUPPORTED if hyp.status in (HypothesisStatus.GENERATED, HypothesisStatus.INVESTIGATING) else hyp.status
                hyp.update_assessment(
                    status=new_status,
                    reasoning=f"{hyp.reasoning}\n{assessment.reason}".strip() if hyp.reasoning else assessment.reason,
                )

            elif assessment.assessment == AssessmentType.CONTRADICTS:
                hyp.add_contradicting_evidence(ev_id)
                new_status = HypothesisStatus.WEAKENED if hyp.status in (HypothesisStatus.GENERATED, HypothesisStatus.INVESTIGATING, HypothesisStatus.SUPPORTED) else hyp.status
                hyp.update_assessment(
                    status=new_status,
                    reasoning=f"{hyp.reasoning}\n{assessment.reason}".strip() if hyp.reasoning else assessment.reason,
                )
