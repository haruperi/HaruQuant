"""Tool allowlist enforcement for agent runtime calls."""

from __future__ import annotations

from dataclasses import dataclass

from backend.agents.permissions import AgentToolPermissionService

from haruquant.utils import logger

class ToolPolicyError(ValueError):
    """Raised when an agent requests a disallowed tool."""


@dataclass(frozen=True)
class ToolAllowlistDecision:
    allowed_tools: tuple[str, ...]
    blocked_tools: tuple[str, ...]

    @property
    def allowed(self) -> bool:
        return not self.blocked_tools


class ToolAllowlistMiddleware:
    """Validate that requested tools stay within the declared allowlist."""

    def __init__(self, permission_service: AgentToolPermissionService | None = None) -> None:
        self.permission_service = permission_service

    def evaluate(
        self,
        *,
        allowed_tools: tuple[str, ...],
        requested_tools: tuple[str, ...],
    ) -> ToolAllowlistDecision:
        allowed = set(allowed_tools)
        blocked = tuple(tool_name for tool_name in requested_tools if tool_name not in allowed)
        permitted = tuple(tool_name for tool_name in requested_tools if tool_name in allowed)
        return ToolAllowlistDecision(
            allowed_tools=permitted,
            blocked_tools=blocked,
        )

    def enforce(
        self,
        *,
        allowed_tools: tuple[str, ...],
        requested_tools: tuple[str, ...],
    ) -> ToolAllowlistDecision:
        decision = self.evaluate(
            allowed_tools=allowed_tools,
            requested_tools=requested_tools,
        )
        if not decision.allowed:
            blocked = ", ".join(decision.blocked_tools)
            raise ToolPolicyError(f"disallowed tools requested: {blocked}")
        return decision

    def enforce_agent_tool(
        self,
        *,
        agent_name: str,
        tool_name: str,
        has_human_approval: bool = False,
        has_risk_governor_approval: bool = False,
    ):
        """Enforce the Phase 5 registry-backed agent permission layer."""

        service = self.permission_service or AgentToolPermissionService()
        try:
            return service.enforce(
                agent_name=agent_name,
                tool_name=tool_name,
                has_human_approval=has_human_approval,
                has_risk_governor_approval=has_risk_governor_approval,
            )
        except PermissionError as exc:
            raise ToolPolicyError(str(exc)) from exc
