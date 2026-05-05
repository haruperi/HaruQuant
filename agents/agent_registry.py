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
    "market_intelligence": "market_intelligence",
    "technical_analyst": "technical_analyst",
    "strategy_scout": "strategy_scout",
    "strategy_creator": "strategy_creator",
    "strategy_reviewer": "strategy_reviewer",
    "codegen": "codegen",
    "backtest": "backtest",
    "backtest_analyst": "backtest_analyst",
    "optimization": "optimization",
    "optimization_comparator": "optimization_comparator",
    "robustness": "robustness",
    "robustness_scorecard": "robustness_scorecard",
    "statistical_validation": "statistical_validation",
    "risk_reviewer": "risk_reviewer",
    "portfolio_manager": "portfolio_manager",
    "execution": "execution",
    "paper_execution": "paper_execution",
    "live_execution": "live_execution",
    "bull_researcher": "bull_researcher",
    "bear_researcher": "bear_researcher",
    "synthesis_trader": "synthesis_trader",
    "incident_agent": "incident_agent",
    "cost_optimizer": "cost_optimizer",
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
            "market_intelligence": "Read-only market regime and spread intelligence",
            "technical_analyst": "Read-only technical context analyst",
            "strategy_scout": "Read-only strategy idea scout",
            "strategy_creator": "Strategy specification creator",
            "strategy_reviewer": "Strategy quality reviewer",
            "codegen": "Strategy code generator",
            "backtest": "Backtest and simulation operator",
            "backtest_analyst": "Backtest diagnosis analyst",
            "optimization": "Optimization comparison specialist",
            "optimization_comparator": "Optimization robustness comparator",
            "robustness": "Robustness stress-testing specialist",
            "robustness_scorecard": "Robustness scorecard reviewer",
            "statistical_validation": "Statistical robustness validator",
            "risk_reviewer": "Risk and policy reviewer",
            "portfolio_manager": "Portfolio allocation reviewer",
            "execution": "Execution proposal specialist",
            "paper_execution": "Paper execution simulation operator",
            "live_execution": "Live execution agent guarded by deterministic gates",
            "bull_researcher": "Evidence-bound bullish debate researcher",
            "bear_researcher": "Evidence-bound bearish debate researcher",
            "synthesis_trader": "Synthesis trader that recommends but never places orders",
            "incident_agent": "Incident summarization and escalation reviewer",
            "cost_optimizer": "Model and compute cost optimizer",
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
