"""Agent tool contracts.

Tools are the controlled public interface agents use to reach HaruQuant
services. Deterministic implementation stays in `services`.
"""

from .permissions import ToolPermissionError, assert_tool_call_allowed
from .registry import TOOL_REGISTRY, get_tool, list_tools, list_tools_for_agent
from .schemas import ToolDefinition

__all__ = [
    "TOOL_REGISTRY",
    "ToolDefinition",
    "ToolPermissionError",
    "assert_tool_call_allowed",
    "get_tool",
    "list_tools",
    "list_tools_for_agent",
]
