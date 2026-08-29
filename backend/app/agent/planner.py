from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.agent.state import InvestigationState


class AgentAction(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    target_hypotheses: List[str] = Field(default_factory=list)
    missing_evidence_addressed: List[str] = Field(default_factory=list)


def calculate_diagnostic_usefulness(
    action: AgentAction,
    hypotheses: List[Hypothesis],
    missing_evidence: List[str],
) -> float:
    score = 0.0
    hyp_dict = {h.id: h for h in hypotheses}
    
    score += len(action.missing_evidence_addressed) * 2.0
    
    for hyp_id in action.target_hypotheses:
        hyp = hyp_dict.get(hyp_id)
        if hyp:
            if hyp.status == HypothesisStatus.INVESTIGATING:
                score += 3.0
            elif hyp.status in (HypothesisStatus.GENERATED, HypothesisStatus.SUPPORTED):
                score += 2.0
            elif hyp.status == HypothesisStatus.WEAKENED:
                score += 1.0
            elif hyp.status in (HypothesisStatus.CONFIRMED, HypothesisStatus.REJECTED):
                score += 0.1
        else:
            score += 1.0
            
    return score


class Planner:
    def plan(
        self,
        state: InvestigationState,
        hypotheses: List[Hypothesis],
        missing_evidence: List[str],
        available_tools: List[Dict[str, Any]],
    ) -> Tuple[List[AgentAction], Optional[AgentAction]]:
        candidates = self.generate_candidate_actions(
            state, hypotheses, missing_evidence, available_tools
        )
        
        ranked_candidates = sorted(
            candidates,
            key=lambda act: calculate_diagnostic_usefulness(act, hypotheses, missing_evidence),
            reverse=True,
        )
        
        valid_action: Optional[AgentAction] = None
        for act in ranked_candidates:
            if not self._is_duplicate_action(act, state.actions_taken):
                valid_action = act
                break

        return ranked_candidates, valid_action

    def generate_candidate_actions(
        self,
        state: InvestigationState,
        hypotheses: List[Hypothesis],
        missing_evidence: List[str],
        available_tools: List[Dict[str, Any]],
    ) -> List[AgentAction]:
        candidates: List[AgentAction] = []

        active_hypotheses = [
            h for h in hypotheses
            if h.status in (HypothesisStatus.INVESTIGATING, HypothesisStatus.GENERATED, HypothesisStatus.SUPPORTED)
        ]
        target_hyp_ids = [h.id for h in active_hypotheses] or [h.id for h in hypotheses]

        for tool in available_tools:
            tool_name = tool.get("name", "")
            
            tool_missing_addressed = [
                me for me in missing_evidence
                if tool_name.lower() in me.lower() or me.lower() in tool_name.lower()
            ]

            args: Dict[str, Any] = {}
            if "required_params" in tool:
                for param in tool["required_params"]:
                    if param in state.incident:
                        args[param] = state.incident[param]
                    elif param == "time_window" and state.time_window:
                        args[param] = state.time_window

            reason = f"Gather evidence using {tool_name} to test targeted hypotheses"
            if tool_missing_addressed:
                reason += f" and address missing evidence: {', '.join(tool_missing_addressed)}"

            candidates.append(
                AgentAction(
                    tool=tool_name,
                    arguments=args,
                    reason=reason,
                    target_hypotheses=target_hyp_ids,
                    missing_evidence_addressed=tool_missing_addressed,
                )
            )

        return candidates

    def _is_duplicate_action(
        self, action: AgentAction, actions_taken: List[Dict[str, Any]]
    ) -> bool:
        for taken in actions_taken:
            taken_tool = taken.get("tool")
            taken_args = taken.get("arguments", {})
            if taken_tool == action.tool and taken_args == action.arguments:
                return True
        return False
