"""Permission profile for Simulation Department tools."""

from __future__ import annotations

SIMULATION_DEPARTMENT_PERMISSIONS = {
    "can_read_strategy_specs": True,
    "can_read_strategy_code": True,
    "can_read_market_data": True,
    "can_read_backtest_results": True,
    "can_read_analytics_results": True,
    "can_write_backtest_artifacts": True,
    "can_write_simulation_memory": True,
    "can_run_backtests": True,
    "can_run_optimizations": True,
    "can_run_robustness_tests": True,
    "can_run_statistical_tests": True,
    "can_generate_reports": True,
    "can_modify_strategy_code": False,
    "can_approve_risk": False,
    "can_execute_trade": False,
    "can_modify_broker_account": False,
    "can_deploy_strategy_live": False,
}

FORBIDDEN_TOOLS = {
    "execute_trade",
    "place_trade",
    "approve_risk",
    "approve_live_deployment",
    "modify_strategy_code",
    "delete_finalized_evidence",
}


def assert_simulation_tool_allowed(tool_name: str) -> None:
    if tool_name in FORBIDDEN_TOOLS:
        raise PermissionError(f"{tool_name} is forbidden for Simulation Department agents")
