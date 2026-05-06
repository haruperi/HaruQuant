"""AI Chat read-only HaruQuant tools."""

from tools.read_only.contracts import ReadOnlyToolDefinition, ReadOnlyToolRequest, ReadOnlyToolResult
from tools.read_only.state import READ_ONLY_TOOLS


def list_read_only_tool_definitions() -> list[ReadOnlyToolDefinition]:
    return [
        ReadOnlyToolDefinition(
            tool_id=name,
            display_name=name.replace("_", " ").title(),
            description=f"Read-only access to HaruQuant {name.replace('_', ' ')}.",
            input_schema=ReadOnlyToolRequest.model_json_schema(),
            output_schema=ReadOnlyToolResult.model_json_schema(),
        )
        for name in sorted(READ_ONLY_TOOLS)
    ]


__all__ = [
    "READ_ONLY_TOOLS",
    "ReadOnlyToolDefinition",
    "ReadOnlyToolRequest",
    "ReadOnlyToolResult",
    "list_read_only_tool_definitions",
]
