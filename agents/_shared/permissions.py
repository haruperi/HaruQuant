"""Agent permission layer for Phase 5 tool governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from tools.registry import DEFAULT_TOOL_REGISTRY, ToolDefinition, ToolRegistry


class AgentToolPermissionError(PermissionError):
    """Raised when an agent tool call is blocked by policy."""


@dataclass(frozen=True)
class AgentToolPermissionDecision:
    agent_name: str
    tool_name: str
    allowed: bool
    reason: str
    tool_definition: ToolDefinition | None = None
    checked_at: str = ""


@dataclass(frozen=True)
class BlockedToolAttempt:
    agent_name: str
    tool_name: str
    reason: str
    checked_at: str


AGENT_TOOL_ALIASES = {
    "audit_agent": "audit",
    "backtest_agent": "backtest",
    "ceo_agent": "ceo",
    "execution_agent": "execution",
    "live_execution_agent": "live_execution",
    "paper_execution_agent": "paper_execution",
    "performance_reporter_agent": "performance_reporter",
    "planner_agent": "planner",
    "portfolio_manager_agent": "portfolio_manager",
    "research_agent": "research",
    "risk_reviewer_agent": "risk_reviewer",
    "strategy_creator_agent": "strategy_creator",
    "strategy_reviewer_agent": "strategy_reviewer",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_agent_name(agent_name: str) -> str:
    return AGENT_TOOL_ALIASES.get(agent_name, agent_name)


class AgentToolPermissionService:
    """Evaluates agent tool calls against the registry metadata."""

    def __init__(self, registry: ToolRegistry = DEFAULT_TOOL_REGISTRY) -> None:
        self.registry = registry
        self._blocked_attempts: list[BlockedToolAttempt] = []

    @property
    def blocked_attempts(self) -> tuple[BlockedToolAttempt, ...]:
        return tuple(self._blocked_attempts)

    def evaluate(
        self,
        *,
        agent_name: str,
        tool_name: str,
        has_human_approval: bool = False,
        has_risk_governor_approval: bool = False,
    ) -> AgentToolPermissionDecision:
        checked_at = _now()
        normalized_agent = normalize_agent_name(agent_name)
        try:
            tool = self.registry.require(tool_name)
        except Exception:
            return self._blocked(
                agent_name=agent_name,
                tool_name=tool_name,
                reason="unknown_tool",
                checked_at=checked_at,
            )

        allowed_agents = tool.allowed_agents or []
        if not tool.enabled:
            return self._blocked_decision(
                agent_name,
                tool_name,
                "tool_disabled",
                checked_at,
                tool,
            )
        if "*" not in allowed_agents and normalized_agent not in allowed_agents:
            return self._blocked_decision(
                agent_name,
                tool_name,
                "tool_not_allowed_for_agent",
                checked_at,
                tool,
            )
        if tool.risk_level == "critical" and not has_human_approval:
            return self._blocked_decision(
                agent_name,
                tool_name,
                "missing_human_approval",
                checked_at,
                tool,
            )
        if tool.requires_human_approval and not has_human_approval:
            return self._blocked_decision(
                agent_name,
                tool_name,
                "missing_human_approval",
                checked_at,
                tool,
            )
        if tool.requires_risk_governor and not has_risk_governor_approval:
            return self._blocked_decision(
                agent_name,
                tool_name,
                "missing_risk_governor_approval",
                checked_at,
                tool,
            )

        return AgentToolPermissionDecision(
            agent_name=agent_name,
            tool_name=tool_name,
            allowed=True,
            reason="allowed",
            tool_definition=tool,
            checked_at=checked_at,
        )

    def enforce(
        self,
        *,
        agent_name: str,
        tool_name: str,
        has_human_approval: bool = False,
        has_risk_governor_approval: bool = False,
    ) -> AgentToolPermissionDecision:
        decision = self.evaluate(
            agent_name=agent_name,
            tool_name=tool_name,
            has_human_approval=has_human_approval,
            has_risk_governor_approval=has_risk_governor_approval,
        )
        if not decision.allowed:
            raise AgentToolPermissionError(
                f"{decision.reason}: agent={agent_name}, tool={tool_name}"
            )
        return decision

    def _blocked(
        self,
        *,
        agent_name: str,
        tool_name: str,
        reason: str,
        checked_at: str,
    ) -> AgentToolPermissionDecision:
        self._blocked_attempts.append(
            BlockedToolAttempt(
                agent_name=agent_name,
                tool_name=tool_name,
                reason=reason,
                checked_at=checked_at,
            )
        )
        return AgentToolPermissionDecision(
            agent_name=agent_name,
            tool_name=tool_name,
            allowed=False,
            reason=reason,
            checked_at=checked_at,
        )

    def _blocked_decision(
        self,
        agent_name: str,
        tool_name: str,
        reason: str,
        checked_at: str,
        tool: ToolDefinition,
    ) -> AgentToolPermissionDecision:
        self._blocked_attempts.append(
            BlockedToolAttempt(
                agent_name=agent_name,
                tool_name=tool_name,
                reason=reason,
                checked_at=checked_at,
            )
        )
        return AgentToolPermissionDecision(
            agent_name=agent_name,
            tool_name=tool_name,
            allowed=False,
            reason=reason,
            tool_definition=tool,
            checked_at=checked_at,
        )


__all__ = [
    "AgentToolPermissionDecision",
    "AgentToolPermissionError",
    "AgentToolPermissionService",
    "BlockedToolAttempt",
    "normalize_agent_name",
]
