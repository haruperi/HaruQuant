"""Risk Department contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

RiskDecisionStatus = Literal["approved", "approved_with_reduced_size", "rejected", "blocked", "needs_more_context", "error_fail_closed"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RiskProposal:
    proposal_id: str
    proposal_type: str = "trade"
    source_department: str = "portfolio"
    source_agent: str = "execution_planner_agent"
    strategy_id: str = "strategy-unknown"
    strategy_name: str = "strategy-unknown"
    strategy_version: str = "0.1.0"
    strategy_code_hash: str = "unknown"
    strategy_lifecycle_state: str = "paper_approved"
    symbol: str = "UNKNOWN"
    asset_class: str = "forex"
    timeframe: str = "H1"
    side: str = "buy"
    order_type: str = "market"
    requested_volume: float = 0.0
    requested_price: float = 1.0
    stop_loss: float | None = None
    take_profit: float | None = None
    expected_entry_time: str | None = None
    expected_holding_period: str | None = None
    setup_id: str | None = None
    group_id: str | None = None
    risk_model: dict[str, Any] = field(default_factory=dict)
    strategy_risk_controls: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    context_revision: str | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class RiskApprovalToken:
    approval_id: str
    decision_id: str
    proposal_id: str
    strategy_id: str
    strategy_code_hash: str
    symbol: str
    side: str
    order_type: str
    requested_volume: float
    approved_volume: float
    max_price_deviation: float
    account_id: str
    broker_id: str
    valid_from: str
    expires_at: str
    single_use: bool
    used_at: str | None
    risk_metrics_snapshot: dict[str, Any]
    portfolio_state_hash: str
    market_state_hash: str
    config_version_hash: str
    policy_version: str
    signature: str
    audit_ref: str


@dataclass(frozen=True)
class RiskGovernorDecision:
    approval_id: str
    proposal_id: str
    decision: RiskDecisionStatus
    approved_size: float
    expires_at: str
    risk_metrics_snapshot: dict[str, Any]
    config_version_hash: str
    signature: str
    reasons: list[str] = field(default_factory=list)
    decision_id: str = ""
    requested_volume: float = 0.0
    approved_volume: float = 0.0
    risk_level: str = "low"
    rules_checked: list[str] = field(default_factory=list)
    rules_passed: list[str] = field(default_factory=list)
    rules_failed: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_actions: list[str] = field(default_factory=list)
    approval_token_ref: str | None = None
    approval_token: dict[str, Any] | None = None
    policy_version: str = "risk_policy_v1"
    created_at: str = field(default_factory=utc_now)
    audit_ref: str | None = None


@dataclass(frozen=True)
class RiskMemo:
    memo_id: str
    strategy_id: str
    strategy_name: str
    strategy_lifecycle_state: str
    risk_governor_decision_ref: str
    evidence_reviewed: list[str]
    risk_summary: str
    key_risk_metrics: dict[str, Any]
    portfolio_impact: dict[str, Any]
    correlation_concerns: list[str]
    drawdown_concerns: list[str]
    cost_concerns: list[str]
    margin_concerns: list[str]
    robustness_concerns: list[str]
    statistical_concerns: list[str]
    failure_modes: list[str]
    recommendation: str
    required_board_action: str
    required_next_steps: list[str]
    confidence: str
    evidence_refs: list[str]
    audit: dict[str, Any]
