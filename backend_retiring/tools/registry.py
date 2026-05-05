"""Typed Agentic Firm tool registry.

The registry is metadata-only: it describes tool capabilities, schemas, risk
class, approval requirements, and audit requirements. Actual execution remains
inside existing service, MCP, and runtime boundaries.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ToolRiskLevel = Literal["read_only", "write", "critical"]


class ToolRegistryError(ValueError):
    """Raised for invalid tool registry operations."""


class ToolDefinition(BaseModel):
    """One governed tool definition."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel
    permission_required: str = Field(min_length=1)
    requires_human_approval: bool = False
    requires_risk_governor: bool = False
    audit_required: bool = True
    domain: str = Field(min_length=1)
    execution_boundary: str = Field(min_length=1)
    enabled: bool = True


class ToolRegistry:
    """In-memory registry for firm-governed tool metadata."""

    def __init__(self, definitions: list[ToolDefinition] | None = None) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._definitions:
            raise ToolRegistryError(f"tool already registered: {definition.name}")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def require(self, name: str) -> ToolDefinition:
        definition = self.get(name)
        if definition is None:
            raise ToolRegistryError(f"unknown tool: {name}")
        return definition

    def list_tools(
        self,
        *,
        risk_level: ToolRiskLevel | None = None,
        domain: str | None = None,
        enabled_only: bool = True,
    ) -> tuple[ToolDefinition, ...]:
        definitions = self._definitions.values()
        if risk_level is not None:
            definitions = [item for item in definitions if item.risk_level == risk_level]
        if domain is not None:
            definitions = [item for item in definitions if item.domain == domain]
        if enabled_only:
            definitions = [item for item in definitions if item.enabled]
        return tuple(sorted(definitions, key=lambda item: item.name))

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))


def _schema(required: tuple[str, ...] = (), **properties: str) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(required),
        "properties": {
            name: {"type": type_name}
            for name, type_name in properties.items()
        },
        "additionalProperties": False,
    }


def _tool(
    *,
    name: str,
    description: str,
    risk_level: ToolRiskLevel,
    permission_required: str,
    domain: str,
    execution_boundary: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
    requires_human_approval: bool = False,
    requires_risk_governor: bool = False,
    audit_required: bool = True,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        input_schema=input_schema or _schema(),
        output_schema=output_schema or {"type": "object"},
        risk_level=risk_level,
        permission_required=permission_required,
        requires_human_approval=requires_human_approval,
        requires_risk_governor=requires_risk_governor,
        audit_required=audit_required,
        domain=domain,
        execution_boundary=execution_boundary,
    )


DEFAULT_TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    # Read-only tools.
    _tool(
        name="get_symbol_data",
        description="Read historical or cached symbol OHLCV data.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="data",
        execution_boundary="backend_retiring.tools.data_tools",
        input_schema=_schema(("symbol",), symbol="string", timeframe="string", count="integer"),
    ),
    _tool(
        name="get_latest_ohlcv",
        description="Read latest OHLCV candle data for a symbol and timeframe.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="data",
        execution_boundary="backend_retiring.tools.data_tools",
        input_schema=_schema(("symbol", "timeframe"), symbol="string", timeframe="string"),
    ),
    _tool(
        name="get_strategy",
        description="Read a strategy record or active version.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="strategy",
        execution_boundary="backend_retiring.tools.strategy_tools",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
    ),
    _tool(
        name="list_strategies",
        description="List strategies visible to the requesting scope.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="strategy",
        execution_boundary="backend_retiring.tools.strategy_tools",
    ),
    _tool(
        name="get_backtest_result",
        description="Read a backtest result summary and evidence references.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="backtest",
        execution_boundary="backend_retiring.tools.backtest_tools",
        input_schema=_schema(("backtest_id",), backtest_id="string"),
    ),
    _tool(
        name="get_analytics_summary",
        description="Read analytics summary metrics.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="analytics",
        execution_boundary="backend_retiring.tools.analytics_tools",
    ),
    _tool(
        name="get_open_positions",
        description="Read current open positions.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="portfolio",
        execution_boundary="backend_retiring.tools.portfolio_tools",
    ),
    _tool(
        name="get_account_snapshot",
        description="Read account state snapshot.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="portfolio",
        execution_boundary="backend_retiring.tools.portfolio_tools",
    ),
    _tool(
        name="get_risk_snapshot",
        description="Read risk state, exposure, drawdown, and concentration summary.",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="risk",
        execution_boundary="backend_retiring.tools.risk_tools",
    ),
    # Write tools.
    _tool(
        name="create_strategy_spec",
        description="Persist a structured strategy specification draft.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="strategy",
        execution_boundary="backend_retiring.tools.strategy_tools",
        input_schema=_schema(("strategy_name", "symbol", "timeframe"), strategy_name="string", symbol="string", timeframe="string"),
    ),
    _tool(
        name="save_strategy_code",
        description="Save generated or reviewed strategy code artifact.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="strategy",
        execution_boundary="backend_retiring.tools.strategy_tools",
        input_schema=_schema(("strategy_id", "code"), strategy_id="string", code="string"),
    ),
    _tool(
        name="run_backtest",
        description="Run a governed backtest job.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="backtest",
        execution_boundary="backend_retiring.mcp.backtest_mcp",
        input_schema=_schema(("strategy_id", "symbol", "timeframe"), strategy_id="string", symbol="string", timeframe="string"),
    ),
    _tool(
        name="run_optimization",
        description="Run a governed optimization job.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="optimization",
        execution_boundary="backend_retiring.mcp.optimization_mcp",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
    ),
    _tool(
        name="run_robustness_test",
        description="Run robustness validation such as walk-forward or Monte Carlo checks.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="robustness",
        execution_boundary="services.optimization",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
    ),
    _tool(
        name="create_risk_review",
        description="Persist an advisory risk review memo.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="risk",
        execution_boundary="backend_retiring.tools.risk_tools",
        input_schema=_schema(("review_id",), review_id="string"),
    ),
    _tool(
        name="create_report",
        description="Create a human-readable report artifact.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="reporting",
        execution_boundary="backend_retiring.tools.reporting_tools",
        input_schema=_schema(("report_type",), report_type="string"),
    ),
    _tool(
        name="start_paper_trading",
        description="Admit a reviewed strategy to paper trading workflow.",
        risk_level="write",
        permission_required="T2_WRITE",
        domain="execution",
        execution_boundary="backend_retiring.execution.paper_broker",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
        requires_risk_governor=True,
    ),
    # Critical tools.
    _tool(
        name="request_live_activation",
        description="Request Human Board approval for live activation.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="portfolio",
        execution_boundary="services.execution.approval",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
        requires_human_approval=True,
    ),
    _tool(
        name="create_trade_proposal",
        description="Create a trade proposal that must pass deterministic risk review.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="execution",
        execution_boundary="backend_retiring.contracts.trade_proposal",
        input_schema=_schema(("strategy_id", "symbol", "side"), strategy_id="string", symbol="string", side="string"),
        requires_risk_governor=True,
    ),
    _tool(
        name="request_risk_approval",
        description="Request deterministic RiskGovernor approval for a proposal.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="risk",
        execution_boundary="backend_retiring.risk.governor",
        input_schema=_schema(("proposal_id",), proposal_id="string"),
        requires_risk_governor=True,
    ),
    _tool(
        name="place_paper_order",
        description="Place a paper order through governed paper execution.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="execution",
        execution_boundary="backend_retiring.execution.paper_broker",
        input_schema=_schema(("execution_request_id",), execution_request_id="string"),
        requires_risk_governor=True,
    ),
    _tool(
        name="place_live_order",
        description="Place a live order through the governed order router.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="execution",
        execution_boundary="backend_retiring.execution.order_router",
        input_schema=_schema(("execution_request_id",), execution_request_id="string"),
        requires_human_approval=True,
        requires_risk_governor=True,
    ),
    _tool(
        name="close_live_position",
        description="Close a live position through governed execution.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="execution",
        execution_boundary="backend_retiring.execution.order_router",
        input_schema=_schema(("position_id",), position_id="string"),
        requires_human_approval=True,
        requires_risk_governor=True,
    ),
    _tool(
        name="pause_strategy",
        description="Pause a strategy through lifecycle governance.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="strategy",
        execution_boundary="services.strategy.governance",
        input_schema=_schema(("strategy_id",), strategy_id="string"),
        requires_human_approval=True,
    ),
    _tool(
        name="disable_live_trading",
        description="Disable live trading entry through governed safety controls.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="execution",
        execution_boundary="services.risk.safety",
        requires_human_approval=True,
    ),
    _tool(
        name="trigger_kill_switch",
        description="Trigger the kill switch and block new entries.",
        risk_level="critical",
        permission_required="T3_CRITICAL",
        domain="risk",
        execution_boundary="backend_retiring.risk.kill_switch",
        requires_human_approval=True,
        requires_risk_governor=True,
    ),
)


DEFAULT_TOOL_REGISTRY = ToolRegistry(list(DEFAULT_TOOL_DEFINITIONS))


def get_default_tool_registry() -> ToolRegistry:
    return DEFAULT_TOOL_REGISTRY


__all__ = [
    "DEFAULT_TOOL_DEFINITIONS",
    "DEFAULT_TOOL_REGISTRY",
    "ToolDefinition",
    "ToolRegistry",
    "ToolRegistryError",
    "ToolRiskLevel",
    "get_default_tool_registry",
]
