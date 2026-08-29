from backend.tools.registry import ToolRegistry, ToolResult


class ToolExecutor:
    """Safe execution boundary for agent tool actions."""

    def __init__(self, registry=None):
        self.registry = registry or ToolRegistry()
        self.allowed_tools = set(self.registry.tools.keys())

    def execute(self, action):
        if not isinstance(action, dict):
            return ToolResult(
                tool="unknown",
                status="error_invalid_action",
                evidence_ids=[],
                observations=["Action must be a dictionary."],
                provenance=[]
            )

        tool_name = action.get("tool")
        arguments = action.get("arguments", {})

        if not isinstance(tool_name, str) or not tool_name:
            return ToolResult(
                tool=str(tool_name or "unknown"),
                status="error_invalid_action",
                evidence_ids=[],
                observations=["Action must contain a tool name."],
                provenance=[]
            )

        if not isinstance(arguments, dict):
            return ToolResult(
                tool=tool_name,
                status="error_invalid_arguments",
                evidence_ids=[],
                observations=["Tool arguments must be an object."],
                provenance=[]
            )

        if tool_name not in self.allowed_tools:
            return ToolResult(
                tool=tool_name,
                status="error_invalid_tool",
                evidence_ids=[],
                observations=[f"Tool not allowed: {tool_name}"],
                provenance=[]
            )

        try:
            result = self.registry.execute(tool_name, **arguments)

            if not isinstance(result, ToolResult):
                return ToolResult(
                    tool=tool_name,
                    status="error_invalid_result",
                    evidence_ids=[],
                    observations=["Tool returned an invalid result."],
                    provenance=[]
                )

            return result

        except TypeError as exc:
            return ToolResult(
                tool=tool_name,
                status="error_invalid_arguments",
                evidence_ids=[],
                observations=[f"Invalid tool arguments: {exc}"],
                provenance=[]
            )
        except Exception as exc:
            return ToolResult(
                tool=tool_name,
                status="error_execution_failed",
                evidence_ids=[],
                observations=[f"Tool execution failed: {exc}"],
                provenance=[]
            )
