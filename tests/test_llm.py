import pytest
from pydantic import ValidationError

from backend.app.agent.llm import (
    ProposedAgentAction,
    proposed_to_agent_action,
    validate_action_proposal,
)


def test_valid_proposal():
    proposal_data = {
        "tool": "get_logs",
        "arguments": {"service": "auth-service"},
        "reason": "Check recent error logs",
        "target_hypotheses": ["hyp-1"],
        "missing_evidence_addressed": ["error_logs"],
    }

    validated = validate_action_proposal(proposal_data, allowed_tools=["get_logs", "get_metrics"])
    assert validated.tool == "get_logs"
    assert validated.arguments == {"service": "auth-service"}
    assert validated.reason == "Check recent error logs"

    action = proposed_to_agent_action(validated)
    assert action.tool == "get_logs"
    assert action.target_hypotheses == ["hyp-1"]


def test_invalid_empty_tool():
    proposal_data = {
        "tool": "   ",
        "arguments": {},
        "reason": "Invalid tool test",
    }
    with pytest.raises(ValidationError):
        validate_action_proposal(proposal_data)


def test_invalid_arguments_type():
    proposal_data = {
        "tool": "get_logs",
        "arguments": "not_a_dict",
        "reason": "Invalid args test",
    }
    with pytest.raises(ValidationError):
        validate_action_proposal(proposal_data)


def test_disallowed_tool_fails_allowlist():
    proposal_data = {
        "tool": "unauthorized_tool",
        "arguments": {},
        "reason": "Testing allowlist",
    }
    with pytest.raises(ValueError, match="is not in the allowed tools list"):
        validate_action_proposal(proposal_data, allowed_tools=["get_logs", "get_metrics"])
