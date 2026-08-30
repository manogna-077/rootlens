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


def _calculate_domain_bonus(tool_name: str, context_text: str) -> float:
    if not context_text or not tool_name:
        return 0.0
    text_lower = context_text.lower()
    tool_lower = tool_name.lower()
    
    DOMAIN_FAMILIES = {
        "deploy": ["deploy", "deployment", "release", "version", "rollback"],
        "metric": ["metric", "metrics", "saturation", "latency", "connection", "cpu", "memory", "spike", "rate_limit"],
        "log": ["log", "logs", "error", "exception", "failure", "trace"],
        "database": ["database", "db", "lock", "sql", "query"],
        "dependency": ["dependency", "provider", "upstream", "external", "third_party", "health"],
    }
    
    bonus = 0.0
    for domain, keywords in DOMAIN_FAMILIES.items():
        if domain in tool_lower or any(kw in tool_lower for kw in keywords):
            if any(kw in text_lower for kw in keywords):
                bonus += 0.5
                break
    return min(1.0, bonus)


def calculate_diagnostic_usefulness(
    action: AgentAction,
    hypotheses: List[Hypothesis],
    missing_evidence: List[str],
    context_text: str = "",
) -> float:
    score = 0.0
    hyp_dict = {h.id: h for h in hypotheses}
    
    # Positional missing evidence priority: index 0 -> +3.0, index 1 -> +2.0, index 2 -> +1.0
    for me in action.missing_evidence_addressed:
        if me in missing_evidence:
            idx = missing_evidence.index(me)
            score += max(1.0, 3.0 - float(idx))
        else:
            score += 1.0

    # Domain alignment bonus
    score += _calculate_domain_bonus(action.tool, context_text)

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
        
        context_str = f"{state.incident.get('description', '')} {state.incident.get('signal', '')} {' '.join(h.statement for h in hypotheses)}"

        ranked_candidates = sorted(
            candidates,
            key=lambda act: calculate_diagnostic_usefulness(act, hypotheses, missing_evidence, context_text=context_str),
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
            if tool_name in ("search_past_incidents", "search_runbooks"):
                query_str = state.incident.get("description", "") or state.goal or "incident"
                args["query"] = query_str
                if "service" in state.incident:
                    args["service"] = state.incident["service"]
            elif "required_params" in tool:
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
