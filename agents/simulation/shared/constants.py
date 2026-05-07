"""Shared Simulation Department constants."""

from __future__ import annotations

DEPARTMENT_NAME = "simulation"
ENGINE_VERSION = "haruquant_simulation_engine_v1"
ANALYTICS_VERSION = "haruquant_analytics_stack_v1"
PERMISSION_PROFILE = "simulation_read_write_artifacts_no_execution_v1"
POLICY_VERSION = "deterministic_policy_v1"
PROMPT_VERSION = "simulation_department_prompt_v1"
SUPPORTED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}
SUPPORTED_EXECUTION_MODES = {"next_bar_open", "close_to_close", "event_driven"}
SUPPORTED_MARGIN_MODES = {None, "netting", "hedging", "cash"}
MIN_TRADE_COUNT = 20
MAX_DRAWDOWN = 0.20
MAX_PROFIT_CONCENTRATION = 0.40
MIN_COST_EDGE_RATIO = 1.0
BLOCKED_ACTIONS = [
    "execute_trade",
    "place_trade",
    "modify_live_position",
    "approve_risk",
    "approve_live_deployment",
    "modify_broker_account",
    "delete_finalized_evidence",
    "hide_failed_results",
]
