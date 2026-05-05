"""Downstream tool-health monitoring helpers."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils.logger import logger

@dataclass(frozen=True)
class ToolHealthResult:
    """Aggregated health status for one downstream tool group."""

    degraded: bool
    status: str
    failing_tools: tuple[str, ...]


def evaluate_tool_health(tool_statuses: dict[str, str]) -> ToolHealthResult:
    """Collapse downstream tool states into a stable degraded/healthy result."""

    failing_tools = tuple(
        tool_name
        for tool_name, status in tool_statuses.items()
        if status not in {"healthy", "disabled"}
    )
    return ToolHealthResult(
        degraded=bool(failing_tools),
        status="degraded" if failing_tools else "healthy",
        failing_tools=failing_tools,
    )
