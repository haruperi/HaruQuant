"""Agent registry for the Phase 6 control plane."""

from __future__ import annotations

from dataclasses import dataclass

from tools.registry import list_tools_for_agent


@dataclass(frozen=True)
class AgentDescriptor:
    agent_name: str
    role: str
    allowed_tools: tuple[str, ...]


_AGENT_ALIASES = {
    "ceo": "ceo",
    "planner": "planner",
    "research": "research",
    "strategy_creator": "strategy_creator",
    "strategy_reviewer": "strategy_reviewer",
    "backtest": "backtest",
    "risk_reviewer": "risk_reviewer",
    "performance_reporter": "performance_reporter",
    "audit": "audit",
}


class AgentRegistry:
    """Registry of the initial HaruQuant firm departments."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDescriptor] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        roles = {
            "ceo": "Operator-facing CEO/CIO orchestrator",
            "planner": "Structured workflow planner",
            "research": "Read-only market and strategy research",
            "strategy_creator": "Strategy specification creator",
            "strategy_reviewer": "Strategy quality reviewer",
            "backtest": "Backtest and simulation operator",
            "risk_reviewer": "Risk and policy reviewer",
            "performance_reporter": "Performance reporting specialist",
            "audit": "Audit and traceability reviewer",
        }
        for agent_name, role in roles.items():
            tools = tuple(tool.name for tool in list_tools_for_agent(agent_name))
            self.register(
                AgentDescriptor(
                    agent_name=agent_name,
                    role=role,
                    allowed_tools=tools,
                )
            )

    def register(self, descriptor: AgentDescriptor) -> None:
        self._agents[descriptor.agent_name] = descriptor

    def require(self, agent_name: str) -> AgentDescriptor:
        key = _AGENT_ALIASES.get(agent_name, agent_name)
        try:
            return self._agents[key]
        except KeyError as exc:
            raise KeyError(f"Unknown agent: {agent_name}") from exc

    def list_agents(self) -> list[AgentDescriptor]:
        return list(self._agents.values())


__all__ = ["AgentDescriptor", "AgentRegistry"]
