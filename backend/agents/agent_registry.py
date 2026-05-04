"""Agent registry for the HaruQuant Agentic Firm control plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.agents.base import BaseAgent, FirmDepartmentAgent
from backend.agents.permissions import AgentToolPermissionService, get_default_permission_service


@dataclass(frozen=True)
class AgentDescriptor:
    """Static metadata for a firm-managed agent."""

    agent_name: str
    role: str
    department: str
    module_path: str
    allowed_tools: tuple[str, ...] = ()
    description: str = ""


DEFAULT_AGENT_DESCRIPTORS: tuple[AgentDescriptor, ...] = (
    AgentDescriptor("ceo", "CEO Agent", "executive", "backend.agents.ceo.agent", description="Owns final user-facing synthesis, escalation, and Board communication."),
    AgentDescriptor("planner", "Planner Agent", "executive", "backend.agents.planner.agent", description="Turns firm requests into governed task plans."),
    AgentDescriptor("research", "Research Agent", "research", "backend.agents.research.agent", description="Collects read-only market and strategy evidence."),
    AgentDescriptor("strategy_creator", "Strategy Creator Agent", "strategy", "backend.agents.strategy_creator.agent", description="Drafts structured strategy specifications."),
    AgentDescriptor("strategy_reviewer", "Strategy Reviewer Agent", "strategy", "backend.agents.strategy_reviewer.agent", description="Reviews strategy quality and lifecycle readiness."),
    AgentDescriptor("backtest", "Backtest Agent", "testing", "backend.agents.backtest.agent", description="Runs and summarizes backtest evidence."),
    AgentDescriptor("risk_reviewer", "Risk Reviewer Agent", "risk", "backend.agents.risk_reviewer.agent", description="Produces advisory risk reviews before deterministic gates."),
    AgentDescriptor("performance_reporter", "Performance Reporter Agent", "reporting", "backend.agents.performance_reporter.agent", description="Creates operating and Board performance reports."),
    AgentDescriptor("audit", "Audit Agent", "audit", "backend.agents.audit.agent", description="Checks trace completeness and policy adherence."),
)


class AgentRegistry:
    """In-memory registry of firm agents and their permission envelopes."""

    def __init__(
        self,
        *,
        permission_service: AgentToolPermissionService | None = None,
        descriptors: Iterable[AgentDescriptor] = DEFAULT_AGENT_DESCRIPTORS,
    ) -> None:
        self.permission_service = permission_service or get_default_permission_service()
        self._descriptors: dict[str, AgentDescriptor] = {}
        for descriptor in descriptors:
            self.register(descriptor)

    def register(self, descriptor: AgentDescriptor) -> AgentDescriptor:
        allowed_tools = descriptor.allowed_tools or self.permission_service.allowed_tools_for_agent(
            descriptor.agent_name
        )
        normalized = AgentDescriptor(
            agent_name=descriptor.agent_name,
            role=descriptor.role,
            department=descriptor.department,
            module_path=descriptor.module_path,
            allowed_tools=tuple(allowed_tools),
            description=descriptor.description,
        )
        self._descriptors[normalized.agent_name] = normalized
        return normalized

    def get(self, agent_name: str) -> AgentDescriptor | None:
        return self._descriptors.get(agent_name)

    def require(self, agent_name: str) -> AgentDescriptor:
        descriptor = self.get(agent_name)
        if descriptor is None:
            raise LookupError(f"agent is not registered: {agent_name}")
        return descriptor

    def list_agents(self) -> tuple[AgentDescriptor, ...]:
        return tuple(self._descriptors[name] for name in sorted(self._descriptors))

    def create_agent(self, agent_name: str) -> BaseAgent:
        descriptor = self.require(agent_name)
        return FirmDepartmentAgent(
            agent_name=descriptor.agent_name,
            role=descriptor.role,
            allowed_tools=descriptor.allowed_tools,
            permission_service=self.permission_service,
        )


DEFAULT_AGENT_REGISTRY = AgentRegistry()


def get_default_agent_registry() -> AgentRegistry:
    return DEFAULT_AGENT_REGISTRY


__all__ = [
    "AgentDescriptor",
    "AgentRegistry",
    "DEFAULT_AGENT_DESCRIPTORS",
    "DEFAULT_AGENT_REGISTRY",
    "get_default_agent_registry",
]
