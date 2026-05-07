"""Runtime middleware for explicit tool allowlists and Phase 5 permissions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from agents._shared.permissions import AgentToolPermissionDecision, AgentToolPermissionService


class ToolPolicyError(PermissionError):
    """Raised when runtime tool policy blocks a request."""


@dataclass(frozen=True)
class ToolAllowlistDecision:
    allowed: bool
    allowed_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]


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
