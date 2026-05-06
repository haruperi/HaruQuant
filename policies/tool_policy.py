"""Allowlist policy for AI Chat read-only tool execution."""

from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "READ_ONLY_TOOL_ALLOWLIST",
    "ReadOnlyToolPolicy",
    "ToolPolicyDecision",
    "ToolPolicyViolation",
]
