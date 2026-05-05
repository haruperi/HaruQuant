from __future__ import annotations

import pytest

from backend_retiring.tools.registry import (
    DEFAULT_TOOL_REGISTRY,
    ToolDefinition,
    ToolRegistry,
    ToolRegistryError,
)


def test_default_tool_registry_contains_phase5_tool_classes() -> None:
    read_only = {tool.name for tool in DEFAULT_TOOL_REGISTRY.list_tools(risk_level="read_only")}
    write = {tool.name for tool in DEFAULT_TOOL_REGISTRY.list_tools(risk_level="write")}
    critical = {tool.name for tool in DEFAULT_TOOL_REGISTRY.list_tools(risk_level="critical")}

    assert {
        "get_symbol_data",
        "get_latest_ohlcv",
        "get_strategy",
        "list_strategies",
        "get_backtest_result",
        "get_analytics_summary",
        "get_open_positions",
        "get_account_snapshot",
        "get_risk_snapshot",
    }.issubset(read_only)
    assert {
        "create_strategy_spec",
        "save_strategy_code",
        "run_backtest",
        "run_optimization",
        "run_robustness_test",
        "create_risk_review",
        "create_report",
        "start_paper_trading",
    }.issubset(write)
    assert {
        "request_live_activation",
        "create_trade_proposal",
        "request_risk_approval",
        "place_paper_order",
        "place_live_order",
        "close_live_position",
        "pause_strategy",
        "disable_live_trading",
        "trigger_kill_switch",
    }.issubset(critical)


def test_critical_execution_tools_have_hard_approval_metadata() -> None:
    place_live_order = DEFAULT_TOOL_REGISTRY.require("place_live_order")
    trigger_kill_switch = DEFAULT_TOOL_REGISTRY.require("trigger_kill_switch")

    assert place_live_order.requires_human_approval is True
    assert place_live_order.requires_risk_governor is True
    assert place_live_order.audit_required is True
    assert trigger_kill_switch.requires_human_approval is True
    assert trigger_kill_switch.requires_risk_governor is True


def test_tool_registry_rejects_duplicate_registration() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        name="x",
        description="Test tool",
        risk_level="read_only",
        permission_required="T1_READ_ONLY",
        domain="test",
        execution_boundary="test",
    )

    registry.register(definition)

    with pytest.raises(ToolRegistryError):
        registry.register(definition)
