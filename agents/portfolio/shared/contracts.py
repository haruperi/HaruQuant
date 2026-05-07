"""Typed contracts shared by Portfolio Department agents and services."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrategyLifecycleState(str, Enum):
    IDEA = "idea"
    SPEC = "spec"
    CODED = "coded"
    REVIEWED = "reviewed"
    BACKTESTED = "backtested"
    DIAGNOSED = "diagnosed"
    OPTIMIZED = "optimized"
    ROBUSTNESS_TESTED = "robustness_tested"
    STATISTICALLY_VALIDATED = "statistically_validated"
    PAPER_CANDIDATE = "paper_candidate"
    PAPER_LIVE = "paper_live"
    MICRO_LIVE_CANDIDATE = "micro_live_candidate"
    MICRO_LIVE = "micro_live"
    LIVE_CANDIDATE = "live_candidate"
    LIVE = "live"
    PAUSED = "paused"
    RETIRED = "retired"
    REJECTED = "rejected"


class PortfolioRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"portfolio-request-{uuid4()}")
    request_type: str = "portfolio_review"
    strategy_id: str | None = None
    strategy_name: str | None = None
    caller: str = "operator"
    permission_profile: str = "portfolio_read_only_v1"
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    board_approval_id: str | None = None


class PortfolioDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"portfolio-decision-{uuid4()}")
    decision_type: str
    strategy_id: str | None = None
    strategy_name: str | None = None
    current_lifecycle_state: StrategyLifecycleState | None = None
    proposed_lifecycle_state: StrategyLifecycleState | None = None
    current_allocation: float = 0.0
    proposed_allocation: float = 0.0
    symbol_exposure_change: dict[str, float] = Field(default_factory=dict)
    currency_cluster_exposure_change: dict[str, float] = Field(default_factory=dict)
    correlation_impact: dict[str, Any] = Field(default_factory=dict)
    risk_governor_constraints: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    required_approval_level: str = "operator"
    board_approval_required: bool = False
    board_approval_id: str | None = None
    decision_status: str = "proposed"
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    risk_level: str = "medium"
    created_at: str = Field(default_factory=now_iso)
    expires_at: str | None = None
    audit_ref: str | None = None


class LifecycleTransitionRequest(BaseModel):
    transition_id: str = Field(default_factory=lambda: f"lifecycle-transition-{uuid4()}")
    strategy_id: str
    old_state: StrategyLifecycleState
    new_state: StrategyLifecycleState
    actor: str = "operator"
    reason: str = "portfolio_lifecycle_review"
    evidence_refs: list[str] = Field(default_factory=list)
    board_approval_id: str | None = None
    risk_governor_compatible: bool = True
    incident_resume_approval: str | None = None
    strategy_code_hash: str | None = None
    strategy_spec_version: str | None = None


class LifecycleTransitionResult(BaseModel):
    transition_id: str
    strategy_id: str
    old_state: StrategyLifecycleState
    new_state: StrategyLifecycleState
    status: str
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    actor: str = "operator"
    created_at: str = Field(default_factory=now_iso)
    audit_ref: str | None = None


class AllocationProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"allocation-proposal-{uuid4()}")
    available_capital: float
    current_allocations: dict[str, float] = Field(default_factory=dict)
    proposed_allocations: dict[str, float] = Field(default_factory=dict)
    lifecycle_states: dict[str, str] = Field(default_factory=dict)
    strategy_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
    symbol_exposure: dict[str, float] = Field(default_factory=dict)
    cluster_exposure: dict[str, float] = Field(default_factory=dict)
    risk_constraints: dict[str, float] = Field(default_factory=dict)
    stale: bool = False
    board_approval_required: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class AllocationDecision(BaseModel):
    proposal_id: str
    status: str
    allocations: dict[str, float] = Field(default_factory=dict)
    constraint_report: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    board_approval_required: bool = False
    audit_ref: str | None = None


class ExecutionProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"execution-proposal-{uuid4()}")
    strategy_id: str
    strategy_name: str | None = None
    strategy_code_hash: str = "unknown"
    strategy_config_hash: str = "unknown"
    symbol: str
    side: str
    order_type: str = "market"
    requested_volume: float
    requested_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    signal_time: str | None = None
    proposal_time: str = Field(default_factory=now_iso)
    signal_reason: str | None = None
    setup_id: str | None = None
    group_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    risk_mode: str = "risk_governor_required"
    execution_mode: str = "paper"
    evidence_refs: list[str] = Field(default_factory=list)


class ExecutionDecision(BaseModel):
    proposal_id: str
    status: str
    approval_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class PaperOrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str = "market"
    requested_volume: float
    requested_price: float = 1.0
    strategy_id: str = "strategy-unknown"


class PaperOrderResult(BaseModel):
    paper_order_id: str
    status: str
    symbol: str
    side: str
    order_type: str
    requested_volume: float
    executed_volume: float
    requested_price: float
    executed_price: float | None = None
    spread_at_execution: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0
    swap_estimate: float = 0.0
    rejection_reason: str | None = None
    created_at: str = Field(default_factory=now_iso)
    audit_ref: str | None = None


class LiveOrderRequest(PaperOrderRequest):
    approval_id: str | None = None
    approval_token: dict[str, Any] | None = None
    broker: str = "mt5"


class LiveOrderResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"execution-{uuid4()}")
    proposal_id: str
    approval_id: str | None = None
    broker: str = "mt5"
    bridge_name: str = "dry_run"
    symbol: str
    side: str
    order_type: str
    requested_volume: float
    executed_volume: float = 0.0
    requested_price: float | None = None
    executed_price: float | None = None
    spread_at_execution: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0
    swap_estimate: float = 0.0
    broker_order_id: str | None = None
    broker_position_id: str | None = None
    broker_response_code: str | None = None
    broker_response_message: str | None = None
    status: str = "rejected"
    rejection_reason: str | None = None
    created_at: str = Field(default_factory=now_iso)
    audit_ref: str | None = None


class OrderRouteRequest(BaseModel):
    route_id: str = Field(default_factory=lambda: f"route-{uuid4()}")
    proposal: ExecutionProposal
    approval_token: dict[str, Any] | None = None
    live_config: dict[str, Any] = Field(default_factory=dict)
    broker_status: dict[str, Any] = Field(default_factory=dict)
    kill_switch_state: str = "healthy"
    audit_logging_available: bool = True


class OrderRouteResult(BaseModel):
    route_id: str
    status: str
    reasons: list[str] = Field(default_factory=list)
    bridge_name: str | None = None
    audit_ref: str | None = None


class BrokerHealthSnapshot(BaseModel):
    broker: str
    heartbeat: str = "healthy"
    connected: bool = True
    last_heartbeat: str = Field(default_factory=now_iso)
    open_positions: int = 0
    pending_orders: int = 0


class ExecutionHealthSnapshot(BaseModel):
    live_mode_enabled: bool = False
    kill_switch_state: str = "healthy"
    audit_logging_available: bool = True
    risk_governor_available: bool = True
    broker_health: list[BrokerHealthSnapshot] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)


class KillSwitchState(BaseModel):
    state: str = "healthy"
    triggered: bool = False
    trigger_reason: str | None = None
    triggered_at: str | None = None
    resume_allowed: bool = True


class IncidentReport(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"incident-{uuid4()}")
    incident_type: str
    severity: str
    trigger: str
    trigger_time: str = Field(default_factory=now_iso)
    detected_by: str = "portfolio_department"
    affected_strategies: list[str] = Field(default_factory=list)
    affected_symbols: list[str] = Field(default_factory=list)
    affected_orders: list[str] = Field(default_factory=list)
    affected_positions: list[str] = Field(default_factory=list)
    kill_switch_state_before: str = "healthy"
    kill_switch_state_after: str = "triggered"
    risk_governor_state: str = "unknown"
    broker_state: str = "unknown"
    audit_state: str = "unknown"
    immediate_action_taken: str = "live_trading_disabled"
    recommended_next_action: str = "manual_review"
    resume_allowed: bool = False
    human_approval_required: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
    audit_ref: str | None = None


class PerformanceReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"performance-report-{uuid4()}")
    report_type: str = "daily"
    status: str = "complete"
    portfolio_pnl: float = 0.0
    drawdown: float = 0.0
    trade_count: int = 0
    strategy_health: dict[str, Any] = Field(default_factory=dict)
    decision_required: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    audit_ref: str | None = None


class AuditFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"audit-finding-{uuid4()}")
    severity: str
    rule: str
    message: str
    affected_ref: str | None = None
    disables_live_trading: bool = False
    created_at: str = Field(default_factory=now_iso)


class CostReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"cost-report-{uuid4()}")
    period: str = "daily"
    total_cost: float = 0.0
    budget: float = 0.0
    by_agent: dict[str, float] = Field(default_factory=dict)
    by_model_provider: dict[str, float] = Field(default_factory=dict)
    anomalies: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    audit_ref: str | None = None
