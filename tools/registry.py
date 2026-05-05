"""Unified agent tool registry.

This module defines the contract for every planned agent tool. The functions in
category modules are intentionally lightweight wrappers; deterministic behavior
belongs in `services`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from .schemas import (
    AnalyticsRequest,
    AuditRequest,
    BacktestRequest,
    BacktestResultSummary,
    CodeRequest,
    DataRequest,
    ExecutionResult,
    LiveOrderRequest,
    PermissionValidationRequest,
    PolicyValidationRequest,
    ReportRequest,
    RiskRequest,
    SimulationRequest,
    StrategyRequest,
    TaskRequest,
    ToolDefinition,
    ToolStubRequest,
    ToolStubResult,
)


class ToolRegistryError(ValueError):
    """Raised when the tool registry is malformed or queried incorrectly."""


class ToolRegistry:
    """Small registry facade used by the Phase 5 permission layer."""

    def __init__(self, tools: Iterable[ToolDefinition] | None = None) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ToolRegistryError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def require(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolRegistryError(f"Unknown tool: {name}") from exc

    def list_tools(
        self,
        *,
        risk_level: str | None = None,
        category: str | None = None,
        enabled: bool | None = None,
    ) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if risk_level is not None:
            tools = [tool for tool in tools if tool.risk_level == risk_level]
        if category is not None:
            tools = [tool for tool in tools if tool.category == category]
        if enabled is not None:
            tools = [tool for tool in tools if tool.enabled is enabled]
        return tools


POLICY_AGENTS = [
    "ceo_agent",
    "planner_agent",
    "orchestrator",
    "risk_reviewer_agent",
    "audit_agent",
]
TASK_AGENTS = [
    "ceo_agent",
    "planner_agent",
    "conversation_orchestrator",
    "task_manager",
    "audit_agent",
]
MEMORY_AGENTS = ["*"]
DATA_AGENTS = [
    "research_agent",
    "market_intelligence_agent",
    "technical_analyst_agent",
    "simulation_agent",
    "risk_governor",
    "prop_firm_compliance_agent",
    "execution_planner_agent",
]
RESEARCH_AGENTS = [
    "research_agent",
    "market_intelligence_agent",
    "strategy_scout_agent",
    "technical_analyst_agent",
    "bull_researcher_agent",
    "bear_researcher_agent",
]
STRATEGY_AGENTS = [
    "strategy_creator_agent",
    "strategy_spec_validator_agent",
    "strategy_reviewer_agent",
    "portfolio_manager_agent",
    "ceo_agent",
]
CODE_AGENTS = [
    "strategy_codegen_agent",
    "strategy_test_generator_agent",
    "strategy_reviewer_agent",
    "audit_agent",
]
SIMULATION_AGENTS = [
    "simulation_agent",
    "simulation_analyst_agent",
    "risk_reviewer_agent",
    "ceo_agent",
]
ANALYTICS_AGENTS = [
    "simulation_agent",
    "simulation_analyst_agent",
    "risk_reviewer_agent",
    "statistical_validation_agent",
    "performance_reporter_agent",
]
RISK_AGENTS = [
    "risk_governor",
    "risk_reviewer_agent",
    "execution_planner_agent",
    "portfolio_manager_agent",
    "audit_agent",
]
PROP_FIRM_AGENTS = [
    "prop_firm_compliance_agent",
    "risk_governor",
    "consistency_rule_agent",
    "audit_agent",
    "execution_planner_agent",
]
PAPER_EXECUTION_AGENTS = [
    "paper_execution_agent",
    "risk_governor",
    "performance_reporter_agent",
    "audit_agent",
]
LIVE_EXECUTION_AGENTS = [
    "execution_planner_agent",
    "live_execution_agent",
    "risk_governor",
    "order_router",
    "audit_agent",
]
BROKER_AGENTS = ["order_router", "live_execution_agent", "audit_agent"]
KILL_SWITCH_AGENTS = [
    "risk_governor",
    "live_execution_agent",
    "execution_planner_agent",
    "audit_agent",
]
REPORTING_AGENTS = [
    "performance_reporter_agent",
    "ceo_agent",
    "audit_agent",
    "board_liaison_agent",
]
AUDIT_AGENTS = ["*"]


POLICY_TOOLS = [
    "read_constitution",
    "read_risk_policy",
    "read_agent_permissions",
    "read_strategy_lifecycle_policy",
    "validate_against_constitution",
    "validate_against_risk_policy",
    "validate_agent_permission",
]
TASK_TOOLS = [
    "create_agent_task",
    "assign_agent_task",
    "start_agent_task",
    "complete_agent_task",
    "fail_agent_task",
    "block_agent_task",
    "create_child_task",
    "get_task_tree",
    "get_task_status",
    "list_active_tasks",
]
MEMORY_TOOLS = [
    "create_evidence_ref",
    "read_evidence_ref",
    "list_evidence_refs",
    "save_research_report",
    "read_research_report",
    "save_strategy_memory",
    "read_strategy_memory",
    "save_performance_memory",
    "read_performance_memory",
    "save_lesson_learned",
    "search_institutional_memory",
    "search_strategy_memory",
    "search_simulation_memory",
    "verify_evidence_integrity",
]
DATA_TOOLS = [
    "list_symbols",
    "get_symbol_metadata",
    "get_ohlcv_data",
    "get_tick_data",
    "get_spread_history",
    "get_session_calendar",
    "get_economic_calendar",
    "get_high_impact_news_events",
    "get_latest_price",
    "get_latest_tick",
    "get_data_freshness",
    "validate_data_quality",
    "detect_missing_bars",
    "detect_duplicate_ticks",
    "detect_bad_spreads",
    "normalize_symbol_data",
]
RESEARCH_TOOLS = [
    "create_market_intelligence_report",
    "create_technical_analysis_report",
    "create_strategy_idea",
    "score_strategy_idea",
    "rank_strategy_ideas",
    "search_internal_research",
    "search_external_research",
    "summarize_research_source",
    "create_bull_case",
    "create_bear_case",
    "create_research_debate_summary",
]
STRATEGY_TOOLS = [
    "create_strategy_spec",
    "read_strategy_spec",
    "update_strategy_spec",
    "validate_strategy_spec",
    "reject_strategy_spec",
    "approve_strategy_spec_for_code_review",
    "create_strategy_version",
    "compare_strategy_versions",
    "set_strategy_lifecycle_state",
    "request_strategy_promotion",
    "request_strategy_demotion",
    "request_strategy_retirement",
]
CODE_TOOLS = [
    "generate_strategy_code",
    "read_strategy_code",
    "save_strategy_code",
    "update_strategy_code",
    "generate_strategy_tests",
    "run_strategy_unit_tests",
    "run_strategy_static_checks",
    "run_lookahead_bias_check",
    "run_repainting_check",
    "run_parameter_sanity_check",
    "create_strategy_code_hash",
    "lock_strategy_code_version",
]
SIMULATION_TOOLS = [
    "create_simulation_request",
    "run_simulation",
    "cancel_simulation",
    "read_simulation_result",
    "list_simulation_runs",
    "compare_simulation_runs",
    "save_simulation_config",
    "save_simulation_trades",
    "save_simulation_orders",
    "save_simulation_deals",
    "save_simulation_equity_curve",
    "save_simulation_metrics",
    "create_simulation_report",
    "lock_simulation_result",
    "run_backtest",
]
ANALYTICS_TOOLS = [
    "calculate_trade_metrics",
    "calculate_return_metrics",
    "calculate_drawdown_metrics",
    "calculate_ratio_metrics",
    "calculate_risk_metrics",
    "calculate_efficiency_metrics",
    "calculate_distribution_metrics",
    "calculate_benchmark_metrics",
    "run_statistical_tests",
    "calculate_long_short_split",
    "calculate_session_performance",
    "calculate_monthly_performance",
    "calculate_regime_performance",
    "calculate_cost_sensitivity",
]
RISK_TOOLS = [
    "get_account_snapshot",
    "get_open_positions",
    "get_pending_orders",
    "calculate_position_risk",
    "calculate_trade_risk",
    "calculate_portfolio_exposure",
    "calculate_symbol_exposure",
    "calculate_currency_cluster_exposure",
    "calculate_usd_cluster_exposure",
    "calculate_correlation_matrix",
    "calculate_correlation_impact",
    "calculate_margin_impact",
    "calculate_var",
    "calculate_cvar",
    "check_daily_loss_limit",
    "check_total_loss_limit",
    "check_portfolio_drawdown_limit",
    "request_risk_approval",
    "approve_trade_proposal",
    "reject_trade_proposal",
    "issue_risk_approval_token",
    "revoke_risk_approval_token",
]
PROP_FIRM_TOOLS = [
    "check_prop_firm_daily_loss",
    "check_prop_firm_total_loss",
    "check_prop_firm_profit_target",
    "check_prop_firm_news_window",
    "check_prop_firm_weekend_rule",
    "check_prop_firm_overnight_rule",
    "check_forbidden_practices",
    "check_ea_automation_compliance",
    "check_allocation_compliance",
    "calculate_consistency_score",
    "check_best_day_rule_threshold",
    "create_prop_firm_compliance_report",
]
PAPER_EXECUTION_TOOLS = [
    "start_paper_trading",
    "stop_paper_trading",
    "place_paper_order",
    "close_paper_position",
    "cancel_paper_order",
    "get_paper_account_snapshot",
    "get_paper_positions",
    "get_paper_trade_log",
    "simulate_spread",
    "simulate_slippage",
    "simulate_commission",
    "simulate_swap",
]
LIVE_EXECUTION_TOOLS = [
    "request_live_activation",
    "activate_live_trading",
    "deactivate_live_trading",
    "create_trade_proposal",
    "create_execution_plan",
    "validate_execution_plan",
    "place_live_order",
    "close_live_position",
    "cancel_live_order",
    "modify_live_order",
]
BROKER_TOOLS = [
    "mt5_get_account_info",
    "mt5_get_symbol_info",
    "mt5_get_latest_tick",
    "mt5_get_positions",
    "mt5_get_orders",
    "mt5_place_order",
    "mt5_close_position",
    "mt5_cancel_order",
    "mt5_modify_order",
    "ctrader_get_account_info",
    "ctrader_get_symbol_info",
    "ctrader_get_latest_tick",
    "ctrader_get_positions",
    "ctrader_get_orders",
    "ctrader_place_order",
    "ctrader_close_position",
    "ctrader_cancel_order",
    "ctrader_modify_order",
]
KILL_SWITCH_TOOLS = [
    "check_kill_switch_status",
    "trigger_kill_switch",
    "clear_kill_switch",
    "pause_all_trading",
    "pause_new_entries",
    "flatten_all_positions",
    "disable_strategy_execution",
]
REPORTING_TOOLS = [
    "create_daily_report",
    "create_weekly_report",
    "create_monthly_report",
    "create_board_report",
    "create_strategy_report",
    "create_simulation_report",
    "create_risk_report",
    "create_compliance_report",
    "create_audit_report",
    "export_report_markdown",
    "export_report_pdf",
    "read_report",
    "list_reports",
]
AUDIT_TOOLS = [
    "append_audit_log",
    "read_audit_log",
    "verify_audit_chain",
    "verify_tool_call_logged",
    "verify_trade_has_risk_approval",
    "verify_strategy_lifecycle_compliance",
    "verify_no_forbidden_tool_use",
    "verify_no_policy_file_tampering",
    "create_audit_finding",
    "escalate_audit_finding",
    "lock_audit_record",
]


def _schema(model: type) -> dict[str, Any]:
    return model.model_json_schema()


def _read_or_write(name: str) -> str:
    read_prefixes = (
        "read_",
        "list_",
        "get_",
        "search_",
        "check_",
        "validate_",
        "verify_",
        "detect_",
        "calculate_",
        "compare_",
        "summarize_",
        "rank_",
        "score_",
    )
    return "read_only" if name.startswith(read_prefixes) else "write"


def _description(name: str, category: str) -> str:
    return f"{name.replace('_', ' ').capitalize()} through the controlled {category} tool interface."


def _definition(
    name: str,
    *,
    category: str,
    allowed_agents: list[str],
    request_model: type = ToolStubRequest,
    result_model: type = ToolStubResult,
    risk_level: str | None = None,
    requires_risk_governor: bool = False,
    requires_human_approval: bool = False,
    enabled: bool = True,
    description: str | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description or _description(name, category),
        category=category,
        risk_level=risk_level or _read_or_write(name),
        input_schema=_schema(request_model),
        output_schema=_schema(result_model),
        allowed_agents=allowed_agents,
        permission_required=f"{category}:{name}",
        domain=category,
        execution_boundary="registered_tool",
        requires_audit=True,
        requires_risk_governor=requires_risk_governor,
        requires_human_approval=requires_human_approval,
        enabled=enabled,
    )


def _definitions(
    names: Iterable[str],
    *,
    category: str,
    allowed_agents: list[str],
    request_model: type = ToolStubRequest,
    result_model: type = ToolStubResult,
    critical: Iterable[str] = (),
    risk_governed: Iterable[str] = (),
    disabled: Iterable[str] = (),
) -> dict[str, ToolDefinition]:
    critical_set = set(critical)
    risk_governed_set = set(risk_governed)
    disabled_set = set(disabled)
    return {
        name: _definition(
            name,
            category=category,
            allowed_agents=allowed_agents,
            request_model=request_model,
            result_model=result_model,
            risk_level="critical" if name in critical_set else None,
            requires_risk_governor=name in risk_governed_set,
            enabled=name not in disabled_set,
        )
        for name in names
    }


PHASE5_READ_ONLY_TOOLS = [
    "get_symbol_data",
    "get_latest_ohlcv",
    "get_strategy",
    "list_strategies",
    "get_backtest_result",
    "get_analytics_summary",
    "get_open_positions",
    "get_account_snapshot",
    "get_risk_snapshot",
]

PHASE5_WRITE_TOOLS = [
    "create_strategy_spec",
    "save_strategy_code",
    "run_backtest",
    "run_optimization",
    "run_robustness_test",
    "create_risk_review",
    "create_report",
    "start_paper_trading",
]

PHASE5_CRITICAL_TOOLS = [
    "request_live_activation",
    "create_trade_proposal",
    "request_risk_approval",
    "place_paper_order",
    "place_live_order",
    "close_live_position",
    "pause_strategy",
    "disable_live_trading",
    "trigger_kill_switch",
]


TOOL_REGISTRY: dict[str, ToolDefinition] = {}
TOOL_REGISTRY.update(
    _definitions(
        POLICY_TOOLS,
        category="policy",
        allowed_agents=POLICY_AGENTS,
        request_model=PolicyValidationRequest,
    )
)

TOOL_REGISTRY.update(
    _definitions(
        PHASE5_READ_ONLY_TOOLS,
        category="phase5_read_only",
        allowed_agents=[
            "ceo",
            "planner",
            "research",
            "strategy_creator",
            "strategy_reviewer",
            "backtest",
            "risk_reviewer",
            "portfolio_manager",
            "performance_reporter",
            "audit",
        ],
        request_model=ToolStubRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PHASE5_WRITE_TOOLS,
        category="phase5_write",
        allowed_agents=[
            "ceo",
            "planner",
            "strategy_creator",
            "strategy_reviewer",
            "backtest",
            "risk_reviewer",
            "performance_reporter",
            "audit",
        ],
        request_model=ToolStubRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PHASE5_CRITICAL_TOOLS,
        category="phase5_critical",
        allowed_agents=[
            "ceo",
            "risk_reviewer",
            "portfolio_manager",
            "execution",
            "paper_execution",
            "live_execution",
            "risk_governor",
            "audit",
        ],
        request_model=ToolStubRequest,
        result_model=ToolStubResult,
        critical=PHASE5_CRITICAL_TOOLS,
        risk_governed=PHASE5_CRITICAL_TOOLS,
    )
)

for _critical_tool_name in PHASE5_CRITICAL_TOOLS:
    _tool = TOOL_REGISTRY[_critical_tool_name]
    TOOL_REGISTRY[_critical_tool_name] = ToolDefinition(
        name=_tool.name,
        description=_tool.description,
        category=_tool.category,
        risk_level="critical",
        input_schema=_tool.input_schema,
        output_schema=_tool.output_schema,
        allowed_agents=_tool.allowed_agents,
        permission_required=_tool.permission_required,
        domain=_tool.domain,
        execution_boundary=_tool.execution_boundary,
        requires_audit=_tool.requires_audit,
        requires_risk_governor=True,
        requires_human_approval=True,
        enabled=_tool.enabled,
    )
TOOL_REGISTRY["validate_agent_permission"] = _definition(
    "validate_agent_permission",
    category="policy",
    allowed_agents=POLICY_AGENTS,
    request_model=PermissionValidationRequest,
    risk_level="read_only",
)
TOOL_REGISTRY.update(
    _definitions(TASK_TOOLS, category="task", allowed_agents=TASK_AGENTS, request_model=TaskRequest)
)
TOOL_REGISTRY.update(
    _definitions(MEMORY_TOOLS, category="memory", allowed_agents=MEMORY_AGENTS)
)
TOOL_REGISTRY.update(
    _definitions(DATA_TOOLS, category="data", allowed_agents=DATA_AGENTS, request_model=DataRequest)
)
TOOL_REGISTRY.update(
    _definitions(RESEARCH_TOOLS, category="research", allowed_agents=RESEARCH_AGENTS)
)
TOOL_REGISTRY.update(
    _definitions(
        STRATEGY_TOOLS,
        category="strategy",
        allowed_agents=STRATEGY_AGENTS,
        request_model=StrategyRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(CODE_TOOLS, category="code", allowed_agents=CODE_AGENTS, request_model=CodeRequest)
)
TOOL_REGISTRY.update(
    _definitions(
        SIMULATION_TOOLS,
        category="simulation",
        allowed_agents=SIMULATION_AGENTS,
        request_model=SimulationRequest,
    )
)
TOOL_REGISTRY["run_backtest"] = _definition(
    "run_backtest",
    description="Run a reproducible HaruQuant backtest.",
    category="backtest",
    allowed_agents=["backtest_agent", *SIMULATION_AGENTS],
    request_model=BacktestRequest,
    result_model=BacktestResultSummary,
    risk_level="write",
)
TOOL_REGISTRY.update(
    _definitions(
        ANALYTICS_TOOLS,
        category="analytics",
        allowed_agents=ANALYTICS_AGENTS,
        request_model=AnalyticsRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        RISK_TOOLS,
        category="risk",
        allowed_agents=RISK_AGENTS,
        request_model=RiskRequest,
        critical=[
            "approve_trade_proposal",
            "issue_risk_approval_token",
            "revoke_risk_approval_token",
        ],
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PROP_FIRM_TOOLS,
        category="prop_firm",
        allowed_agents=PROP_FIRM_AGENTS,
        request_model=RiskRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PAPER_EXECUTION_TOOLS,
        category="paper_execution",
        allowed_agents=PAPER_EXECUTION_AGENTS,
        request_model=LiveOrderRequest,
        critical=[
            "start_paper_trading",
            "stop_paper_trading",
            "place_paper_order",
            "close_paper_position",
            "cancel_paper_order",
        ],
        risk_governed=["place_paper_order", "close_paper_position"],
    )
)
TOOL_REGISTRY.update(
    _definitions(
        LIVE_EXECUTION_TOOLS,
        category="live_execution",
        allowed_agents=LIVE_EXECUTION_AGENTS,
        request_model=LiveOrderRequest,
        result_model=ExecutionResult,
        critical=[
            "activate_live_trading",
            "deactivate_live_trading",
            "place_live_order",
            "close_live_position",
            "cancel_live_order",
            "modify_live_order",
        ],
        risk_governed=[
            "activate_live_trading",
            "place_live_order",
            "close_live_position",
            "cancel_live_order",
            "modify_live_order",
        ],
        disabled=[
            "activate_live_trading",
            "place_live_order",
            "close_live_position",
            "cancel_live_order",
            "modify_live_order",
        ],
    )
)
TOOL_REGISTRY.update(
    _definitions(
        BROKER_TOOLS,
        category="broker",
        allowed_agents=BROKER_AGENTS,
        request_model=LiveOrderRequest,
        result_model=ExecutionResult,
        critical=[
            "mt5_place_order",
            "mt5_close_position",
            "mt5_cancel_order",
            "mt5_modify_order",
            "ctrader_place_order",
            "ctrader_close_position",
            "ctrader_cancel_order",
            "ctrader_modify_order",
        ],
        risk_governed=[
            "mt5_place_order",
            "mt5_close_position",
            "mt5_cancel_order",
            "mt5_modify_order",
            "ctrader_place_order",
            "ctrader_close_position",
            "ctrader_cancel_order",
            "ctrader_modify_order",
        ],
        disabled=[
            "mt5_place_order",
            "mt5_close_position",
            "mt5_cancel_order",
            "mt5_modify_order",
            "ctrader_place_order",
            "ctrader_close_position",
            "ctrader_cancel_order",
            "ctrader_modify_order",
        ],
    )
)
TOOL_REGISTRY.update(
    _definitions(
        KILL_SWITCH_TOOLS,
        category="kill_switch",
        allowed_agents=KILL_SWITCH_AGENTS,
        request_model=RiskRequest,
        critical=[
            "trigger_kill_switch",
            "clear_kill_switch",
            "pause_all_trading",
            "pause_new_entries",
            "flatten_all_positions",
            "disable_strategy_execution",
        ],
        risk_governed=[
            "clear_kill_switch",
            "flatten_all_positions",
            "disable_strategy_execution",
        ],
    )
)
TOOL_REGISTRY.update(
    _definitions(
        REPORTING_TOOLS,
        category="reporting",
        allowed_agents=REPORTING_AGENTS,
        request_model=ReportRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        AUDIT_TOOLS,
        category="audit",
        allowed_agents=AUDIT_AGENTS,
        request_model=AuditRequest,
        critical=["lock_audit_record"],
    )
)

# Re-apply the Phase 5 checklist facade after the broad category registry so
# duplicate names keep the governance posture required by the implementation
# plan.
TOOL_REGISTRY.update(
    _definitions(
        PHASE5_READ_ONLY_TOOLS,
        category="phase5_read_only",
        allowed_agents=[
            "ceo",
            "planner",
            "research",
            "strategy_creator",
            "strategy_reviewer",
            "backtest",
            "risk_reviewer",
            "portfolio_manager",
            "performance_reporter",
            "audit",
        ],
        request_model=ToolStubRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PHASE5_WRITE_TOOLS,
        category="phase5_write",
        allowed_agents=[
            "ceo",
            "planner",
            "strategy_creator",
            "strategy_reviewer",
            "backtest",
            "risk_reviewer",
            "performance_reporter",
            "audit",
        ],
        request_model=ToolStubRequest,
    )
)
TOOL_REGISTRY.update(
    _definitions(
        PHASE5_CRITICAL_TOOLS,
        category="phase5_critical",
        allowed_agents=[
            "ceo",
            "risk_reviewer",
            "portfolio_manager",
            "execution",
            "paper_execution",
            "live_execution",
            "risk_governor",
            "audit",
        ],
        request_model=ToolStubRequest,
        result_model=ToolStubResult,
        critical=PHASE5_CRITICAL_TOOLS,
        risk_governed=PHASE5_CRITICAL_TOOLS,
    )
)
for _critical_tool_name in PHASE5_CRITICAL_TOOLS:
    _tool = TOOL_REGISTRY[_critical_tool_name]
    TOOL_REGISTRY[_critical_tool_name] = ToolDefinition(
        name=_tool.name,
        description=_tool.description,
        category=_tool.category,
        risk_level="critical",
        input_schema=_tool.input_schema,
        output_schema=_tool.output_schema,
        allowed_agents=_tool.allowed_agents,
        permission_required=_tool.permission_required,
        domain=_tool.domain,
        execution_boundary=_tool.execution_boundary,
        requires_audit=_tool.requires_audit,
        requires_risk_governor=True,
        requires_human_approval=True,
        enabled=_tool.enabled,
    )


def get_tool(name: str) -> ToolDefinition:
    try:
        return TOOL_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown tool '{name}'.") from exc


def list_tools(
    *,
    category: str | None = None,
    enabled: bool | None = None,
) -> list[ToolDefinition]:
    tools = list(TOOL_REGISTRY.values())
    if category is not None:
        tools = [tool for tool in tools if tool.category == category]
    if enabled is not None:
        tools = [tool for tool in tools if tool.enabled is enabled]
    return tools


def list_tools_for_agent(agent_name: str) -> list[ToolDefinition]:
    return [
        tool
        for tool in TOOL_REGISTRY.values()
        if "*" in tool.allowed_agents or agent_name in tool.allowed_agents
    ]


def tool_contracts() -> dict[str, dict[str, Any]]:
    return {name: asdict(tool) for name, tool in TOOL_REGISTRY.items()}


def stub_tool_call(
    tool_name: str,
    *,
    payload: dict[str, Any] | None = None,
) -> ToolStubResult:
    tool = get_tool(tool_name)
    return ToolStubResult(
        tool_name=tool.name,
        message=(
            f"Tool '{tool.name}' is registered, but its service implementation "
            "has not been wired yet."
        ),
        data=payload or {},
        audit_required=tool.requires_audit,
    )


def make_stub_function(tool_name: str):
    def _tool(**kwargs: Any) -> ToolStubResult:
        return stub_tool_call(tool_name, payload=kwargs)

    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    _tool.__doc__ = get_tool(tool_name).description
    return _tool


DEFAULT_TOOL_REGISTRY = ToolRegistry(TOOL_REGISTRY.values())


__all__ = [
    "DEFAULT_TOOL_REGISTRY",
    "PHASE5_CRITICAL_TOOLS",
    "PHASE5_READ_ONLY_TOOLS",
    "PHASE5_WRITE_TOOLS",
    "TOOL_REGISTRY",
    "ToolDefinition",
    "ToolRegistry",
    "ToolRegistryError",
    "get_tool",
    "list_tools",
    "list_tools_for_agent",
    "make_stub_function",
    "stub_tool_call",
    "tool_contracts",
]
