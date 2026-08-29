from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from backend.app.agent.planner import AgentAction


class ProposedAgentAction(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    target_hypotheses: List[str] = Field(default_factory=list)
    missing_evidence_addressed: List[str] = Field(default_factory=list)

    @field_validator("tool")
    @classmethod
    def validate_tool_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool must be a non-empty string")
        return v.strip()

    @field_validator("arguments")
    @classmethod
    def validate_arguments_dict(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("arguments must be an object/dict")
        return v

    @field_validator("target_hypotheses", "missing_evidence_addressed")
    @classmethod
    def validate_lists(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("field must be a list")
        return v


def validate_action_proposal(
    proposal_data: Dict[str, Any],
    allowed_tools: Optional[List[str]] = None,
) -> ProposedAgentAction:
    validated = ProposedAgentAction.model_validate(proposal_data)

    if allowed_tools is not None and len(allowed_tools) > 0:
        if validated.tool not in allowed_tools:
            raise ValueError(
                f"Tool '{validated.tool}' is not in the allowed tools list: {allowed_tools}"
            )

    return validated


def proposed_to_agent_action(proposed: ProposedAgentAction) -> AgentAction:
    return AgentAction(
        tool=proposed.tool,
        arguments=proposed.arguments,
        reason=proposed.reason,
        target_hypotheses=proposed.target_hypotheses,
        missing_evidence_addressed=proposed.missing_evidence_addressed,
    )
