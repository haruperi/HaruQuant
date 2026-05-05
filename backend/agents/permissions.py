"""Agent-to-tool permission layer for the Agentic Firm."""

from __future__ import annotations

from dataclasses import dataclass

from haruquant.utils import logger
from backend.tools.registry import ToolDefinition, ToolRegistry, get_default_tool_registry


@dataclass(frozen=True)
class AgentToolPermissionDecision:
    """Result of a tool permission evaluation."""

    agent_name: str
    tool_name: str
    allowed: bool
    reason: str
    tool_definition: ToolDefinition | None = None


class AgentToolPermissionError(PermissionError):
    """Raised when an agent tool call is not permitted."""


READ_ONLY_TOOLS = (
    "get_symbol_data",
    "get_latest_ohlcv",
    "get_strategy",
    "list_strategies",
    "get_backtest_result",
    "get_analytics_summary",
    "get_open_positions",
    "get_account_snapshot",
    "get_risk_snapshot",
)

WRITE_TOOLS = (
    "create_strategy_spec",
    "save_strategy_code",
    "run_backtest",
    "run_optimization",
    "run_robustness_test",
    "create_risk_review",
    "create_report",
    "start_paper_trading",
)

CRITICAL_TOOLS = (
    "request_live_activation",
    "create_trade_proposal",
    "request_risk_approval",
    "place_paper_order",
    "place_live_order",
    "close_live_position",
    "pause_strategy",
    "disable_live_trading",
    "trigger_kill_switch",
)


DEFAULT_AGENT_TOOL_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "ceo": (
        *READ_ONLY_TOOLS,
        "create_report",
        "request_live_activation",
        "pause_strategy",
        "disable_live_trading",
        "trigger_kill_switch",
    ),
    "planner": (
        *READ_ONLY_TOOLS,
        "create_strategy_spec",
        "create_report",
        "create_trade_proposal",
        "request_risk_approval",
    ),
    "research": READ_ONLY_TOOLS,
    "market_intelligence": READ_ONLY_TOOLS,
    "technical_analyst": READ_ONLY_TOOLS,
    "strategy_scout": READ_ONLY_TOOLS,
    "strategy_creator": (
        *READ_ONLY_TOOLS,
        "create_strategy_spec",
    ),
    "strategy_reviewer": (
        *READ_ONLY_TOOLS,
        "create_risk_review",
        "create_report",
    ),
    "codegen": (
        "get_strategy",
        "create_strategy_spec",
        "save_strategy_code",
    ),
    "backtest": (
        "get_strategy",
        "get_symbol_data",
        "get_latest_ohlcv",
        "run_backtest",
        "get_backtest_result",
        "get_analytics_summary",
        "create_report",
    ),
    "optimization": (
        "get_strategy",
        "get_backtest_result",
        "run_optimization",
        "get_analytics_summary",
        "create_report",
    ),
    "robustness": (
        "get_strategy",
        "get_backtest_result",
        "run_robustness_test",
        "get_analytics_summary",
        "create_report",
    ),
    "statistical_validation": (
        "get_backtest_result",
        "get_analytics_summary",
        "create_report",
    ),
    "risk_reviewer": (
        *READ_ONLY_TOOLS,
        "create_risk_review",
        "request_risk_approval",
        "create_report",
    ),
    "portfolio_manager": (
        *READ_ONLY_TOOLS,
        "start_paper_trading",
        "request_live_activation",
        "pause_strategy",
        "create_report",
    ),
    "execution": (
        "get_strategy",
        "get_open_positions",
        "get_account_snapshot",
        "get_risk_snapshot",
        "create_trade_proposal",
        "request_risk_approval",
        "place_paper_order",
        "place_live_order",
        "close_live_position",
    ),
    "performance_reporter": (
        *READ_ONLY_TOOLS,
        "create_report",
    ),
    "audit": (
        *READ_ONLY_TOOLS,
        "create_report",
        "disable_live_trading",
        "trigger_kill_switch",
    ),
    "cost_optimizer": (
        "get_analytics_summary",
        "create_report",
    ),
}


class AgentToolPermissionService:
    """Evaluate whether an agent may call a registered tool."""

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        allowlist: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self.registry = registry or get_default_tool_registry()
        self.allowlist = allowlist or DEFAULT_AGENT_TOOL_ALLOWLIST

    def allowed_tools_for_agent(self, agent_name: str) -> tuple[str, ...]:
        return self.allowlist.get(agent_name, ())

    def evaluate(
        self,
        *,
        agent_name: str,
        tool_name: str,
        has_human_approval: bool = False,
        has_risk_governor_approval: bool = False,
    ) -> AgentToolPermissionDecision:
        definition = self.registry.get(tool_name)
        if definition is None:
            return self._blocked(agent_name, tool_name, "unknown_tool", None)

        allowed_tools = self.allowed_tools_for_agent(agent_name)
        if tool_name not in allowed_tools:
            return self._blocked(agent_name, tool_name, "tool_not_allowed_for_agent", definition)

        if definition.risk_level == "critical" and (
            definition.requires_human_approval or definition.requires_risk_governor
        ):
            if definition.requires_human_approval and not has_human_approval:
                return self._blocked(agent_name, tool_name, "missing_human_approval", definition)
            if definition.requires_risk_governor and not has_risk_governor_approval:
                return self._blocked(agent_name, tool_name, "missing_risk_governor_approval", definition)

        if definition.requires_risk_governor and not has_risk_governor_approval:
            return self._blocked(agent_name, tool_name, "missing_risk_governor_approval", definition)

        return AgentToolPermissionDecision(
            agent_name=agent_name,
            tool_name=tool_name,
            allowed=True,
            reason="allowed",
            tool_definition=definition,
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
                f"agent '{agent_name}' cannot call tool '{tool_name}': {decision.reason}"
            )
        return decision

    @staticmethod
    def _blocked(
        agent_name: str,
        tool_name: str,
        reason: str,
        definition: ToolDefinition | None,
    ) -> AgentToolPermissionDecision:
        logger.warning(
            f"Agent tool call blocked: agent={agent_name} tool={tool_name} reason={reason}"
        )
        return AgentToolPermissionDecision(
            agent_name=agent_name,
            tool_name=tool_name,
            allowed=False,
            reason=reason,
            tool_definition=definition,
        )


DEFAULT_PERMISSION_SERVICE = AgentToolPermissionService()


def get_default_permission_service() -> AgentToolPermissionService:
    return DEFAULT_PERMISSION_SERVICE


__all__ = [
    "AgentToolPermissionDecision",
    "AgentToolPermissionError",
    "AgentToolPermissionService",
    "CRITICAL_TOOLS",
    "DEFAULT_AGENT_TOOL_ALLOWLIST",
    "DEFAULT_PERMISSION_SERVICE",
    "READ_ONLY_TOOLS",
    "WRITE_TOOLS",
    "get_default_permission_service",
]
