"""Runtime middleware for explicit tool allowlists and Phase 5 permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from agents._shared.permissions import AgentToolPermissionDecision, AgentToolPermissionService


class ToolPolicyError(PermissionError):
    """Raised when runtime tool policy blocks a request."""


READ_ONLY_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "portfolio_summary",
        "open_positions",
        "backtest_summary",
        "strategy_parameters",
        "optimization_results",
        "risk_snapshot",
        "alert_history",
        "symbol_stats",
    }
)


class ToolPolicyViolation(PermissionError):
    """Raised when AI Chat requests a disallowed tool."""


@dataclass(frozen=True)
class ToolAllowlistDecision:
    allowed: bool
    allowed_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]


@dataclass(frozen=True)
class ToolPolicyDecision:
    allowed: bool
    tool_name: str
    reason: str


class ReadOnlyToolPolicy:
    """Enforces that AI Chat can only execute explicit read-only tools."""

    def __init__(self, allowlist: frozenset[str] = READ_ONLY_TOOL_ALLOWLIST) -> None:
        self.allowlist = allowlist

    def enforce(self, tool_name: str) -> ToolPolicyDecision:
        if tool_name not in self.allowlist:
            raise ToolPolicyViolation(f"Tool '{tool_name}' is not in the AI Chat read-only allowlist.")
        return ToolPolicyDecision(
            allowed=True,
            tool_name=tool_name,
            reason="read_only_allowlist",
        )


class ToolAllowlistMiddleware:
    """Keeps legacy allowlist checks and adds registry-backed agent checks."""

    def __init__(
        self,
        permission_service: AgentToolPermissionService | None = None,
    ) -> None:
        self.permission_service = permission_service or AgentToolPermissionService()

    def enforce(
        self,
        *,
        allowed_tools: Iterable[str],
        requested_tools: Iterable[str],
    ) -> ToolAllowlistDecision:
        allowed_set = set(allowed_tools)
        requested = tuple(requested_tools)
        blocked = tuple(tool for tool in requested if tool not in allowed_set)
        if blocked:
            raise ToolPolicyError(
                "disallowed tools requested: " + ", ".join(blocked)
            )
        return ToolAllowlistDecision(
            allowed=True,
            allowed_tools=requested,
            blocked_tools=(),
        )

    def enforce_agent_tool(
        self,
        *,
        agent_name: str,
        tool_name: str,
        has_human_approval: bool = False,
        has_risk_governor_approval: bool = False,
    ) -> AgentToolPermissionDecision:
        try:
            return self.permission_service.enforce(
                agent_name=agent_name,
                tool_name=tool_name,
                has_human_approval=has_human_approval,
                has_risk_governor_approval=has_risk_governor_approval,
            )
        except Exception as exc:
            raise ToolPolicyError(str(exc)) from exc


__all__ = [
    "READ_ONLY_TOOL_ALLOWLIST",
    "ReadOnlyToolPolicy",
    "ToolAllowlistDecision",
    "ToolAllowlistMiddleware",
    "ToolPolicyDecision",
    "ToolPolicyError",
    "ToolPolicyViolation",
]
