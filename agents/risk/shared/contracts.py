"""Shared Risk Department agent support."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAgentCapability:
    agent_name: str
    purpose: str
    allowed_actions: tuple[str, ...]
    tool_names: tuple[str, ...]


BLOCKED_ACTIONS = (
    "approve_trade_directly",
    "execute_trade",
    "modify_open_position",
    "override_risk_governor",
    "change_risk_thresholds_without_approval",
)

RISK_DEPARTMENT_PERMISSIONS = {
    "can_read_strategy_evidence": True,
    "can_read_backtest_results": True,
    "can_read_robustness_results": True,
    "can_read_statistical_validation": True,
    "can_read_portfolio": True,
    "can_read_account_state": True,
    "can_read_market_state": True,
    "can_read_risk_config": True,
    "can_create_approval_token": False,
    "can_approve_risk": False,
    "can_execute_trade": False,
    "can_modify_position": False,
    "can_override_execution": False,
    "can_modify_risk_config": False,
}

AGENT_CAPABILITIES = {
    "risk_orchestrator": RiskAgentCapability("risk_orchestrator", "Coordinate risk workflow while preserving RiskGovernor authority.", ("route_to_risk_governor", "route_to_risk_reviewer", "summarize_risk_department_result"), ("risk_governor", "risk_reviewer", "portfolio_risk_monitor")),
    "portfolio_risk_monitor": RiskAgentCapability("portfolio_risk_monitor", "Monitor portfolio-level risk and escalation state.", ("summarize_portfolio_risk", "flag_concentration_risk", "recommend_block_new_trades"), ("exposure_snapshot", "drawdown_state", "margin_impact")),
    "risk_limit_auditor": RiskAgentCapability("risk_limit_auditor", "Validate risk config quality and limits.", ("audit_risk_thresholds", "flag_invalid_config"), ("load_risk_thresholds", "validate_config_hash")),
    "risk_approval_auditor": RiskAgentCapability("risk_approval_auditor", "Verify approval tokens and execution authorization.", ("verify_approval_token", "flag_token_replay"), ("validate_approval_token",)),
}
