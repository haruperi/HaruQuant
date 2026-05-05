"""Permission helpers for controlled agent tool use."""

from __future__ import annotations

from .schemas import ToolDefinition


class ToolPermissionError(PermissionError):
    """Raised when an agent is not allowed to call a tool."""


def assert_tool_enabled(tool: ToolDefinition) -> None:
    if not tool.enabled:
        raise ToolPermissionError(f"Tool '{tool.name}' is disabled.")


def assert_agent_allowed(tool: ToolDefinition, agent_name: str) -> None:
    if "*" in tool.allowed_agents:
        return
    if agent_name not in tool.allowed_agents:
        raise ToolPermissionError(
            f"Agent '{agent_name}' is not allowed to call tool '{tool.name}'."
        )


def assert_risk_governor_token(
    tool: ToolDefinition,
    risk_governor_token: str | None = None,
) -> None:
    if tool.requires_risk_governor and not risk_governor_token:
        raise ToolPermissionError(
            f"Tool '{tool.name}' requires a RiskGovernor approval token."
        )


def assert_human_approval(
    tool: ToolDefinition,
    human_approval_id: str | None = None,
) -> None:
    if tool.requires_human_approval and not human_approval_id:
        raise ToolPermissionError(
            f"Tool '{tool.name}' requires human approval before execution."
        )


def assert_tool_call_allowed(
    tool: ToolDefinition,
    agent_name: str,
    *,
    risk_governor_token: str | None = None,
    human_approval_id: str | None = None,
) -> None:
    """Validate the generic gate conditions before a tool call."""

    assert_tool_enabled(tool)
    assert_agent_allowed(tool, agent_name)
    assert_risk_governor_token(tool, risk_governor_token)
    assert_human_approval(tool, human_approval_id)
