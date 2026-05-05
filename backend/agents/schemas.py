"""Shared Agentic Firm schemas.

This module is the Phase 3 firm-facing schema surface. It intentionally reuses
existing canonical contracts from `backend.contracts` where they already exist,
and defines small agent/workflow models only for gaps that are not covered by
the current contract layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.contracts.execution_intent.model import ExecutionIntent as CanonicalExecutionIntent
from backend.contracts.execution_receipt.model import ExecutionReceipt as CanonicalExecutionReceipt
from backend.contracts.risk_assessment_decision.model import (
    RiskAssessmentDecision as CanonicalRiskAssessmentDecision,
)
from backend.contracts.strategy_blueprint.model import StrategyBlueprint as CanonicalStrategyBlueprint
from backend.contracts.trade_proposal.model import TradeProposal as CanonicalTradeProposal
from backend.contracts.workflow_plan.model import StepFailurePolicy, WorkflowPlan as CanonicalWorkflowPlan
from backend.agents.chat.ai_chat.models import ConversationPlan


class AgentTaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentDecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    ESCALATE = "escalate"
    BLOCK = "block"
    REPORT = "report"


class ToolCallStatus(str, Enum):
    PLANNED = "planned"
    APPROVED = "approved"
    BLOCKED = "blocked"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EvidenceRef(BaseModel):
    """Reference to supporting evidence used by an agent decision."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    uri: str | None = None
    content_hash: str | None = None
    summary: str | None = None
    source_agent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AgentTask(BaseModel):
    """One unit of work assigned within the agentic firm."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_id: str = Field(min_length=1)
    parent_task_id: str | None = None
    workflow_id: str | None = None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    owner_agent: str = Field(min_length=1)
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    priority: int = Field(default=3, ge=0, le=5)
    input_refs: list[EvidenceRef] = Field(default_factory=list)
    expected_output_contract: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "due_at")
    @classmethod
    def _validate_dt(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AgentObservation(BaseModel):
    """Structured observation produced by an agent or tool."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    observation_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    observation_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AgentDecision(BaseModel):
    """Structured decision produced by an agent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    decision_type: AgentDecisionType
    decision: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ToolCallRequest(BaseModel):
    """Typed request for a governed tool call."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tool_call_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    requesting_agent: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = Field(min_length=1, default="read_only")
    requires_human_approval: bool = False
    requires_risk_governor: bool = False
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ToolCallResult(BaseModel):
    """Typed result from a governed tool call."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    status: ToolCallStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("started_at", "completed_at")
    @classmethod
    def _validate_dt(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


AgentPlan = ConversationPlan


class StrategySpec(BaseModel):
    """Formal, testable strategy specification for strategy creation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    strategy_name: str = Field(min_length=1)
    version: str = Field(min_length=1, default="1.0.0")
    market: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    data_requirements: list[str] = Field(default_factory=list)
    entry_logic: list[str] = Field(min_length=1)
    exit_logic: list[str] = Field(min_length=1)
    position_sizing: str | dict[str, Any]
    risk_assumptions: list[str] = Field(default_factory=list)
    cost_assumptions: list[str] = Field(default_factory=list)
    invalid_conditions: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)
    deployment_recommendation: Literal[
        "reject",
        "revise",
        "backtest",
        "robustness",
        "paper_trading_candidate",
    ] = "backtest"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @classmethod
    def from_strategy_blueprint(cls, blueprint: CanonicalStrategyBlueprint) -> "StrategySpec":
        payload = blueprint.payload
        return cls(
            strategy_name=payload.strategy_name,
            version=blueprint.schema_version,
            market=payload.strategy_type,
            symbol=payload.asset_scope.assets[0],
            timeframe=payload.asset_scope.timeframe,
            data_requirements=[
                payload.asset_scope.data_granularity,
                *payload.assumptions_applied,
            ],
            entry_logic=payload.entry_logic,
            exit_logic=payload.exit_logic,
            position_sizing=payload.position_sizing.model_dump(mode="json"),
            risk_assumptions=[
                item
                for item in [
                    payload.risk_management.stop_loss,
                    payload.risk_management.take_profit,
                    *payload.risk_management.additional_rules,
                ]
                if item
            ],
            cost_assumptions=payload.assumption_defaults_used,
            invalid_conditions=[],
            test_plan=[],
            deployment_recommendation="backtest"
            if payload.backtest_readiness == "ready"
            else "revise",
        )


class StrategyReview(BaseModel):
    """Structured strategy review memo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_id: str = Field(min_length=1)
    strategy_name: str = Field(min_length=1)
    reviewer_agent: str = Field(min_length=1)
    verdict: Literal["approve", "revise", "reject"]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BacktestRequest(BaseModel):
    """Request to run a governed backtest."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    start: datetime | None = None
    end: datetime | None = None
    initial_balance: float = Field(gt=0)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class BacktestResultSummary(BaseModel):
    """Compact backtest result summary for agent exchange."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    backtest_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    total_trades: int = Field(ge=0)
    net_profit: float | None = None
    return_pct: float | None = None
    max_drawdown_pct: float | None = None
    sharpe_ratio: float | None = None
    profit_factor: float | None = None
    win_rate_pct: float | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class RiskReview(BaseModel):
    """Advisory risk review memo. Binding approval remains deterministic."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    review_id: str = Field(min_length=1)
    strategy_id: str | None = None
    proposal_id: str | None = None
    reviewer_agent: str = Field(min_length=1)
    verdict: Literal["acceptable", "acceptable_with_limits", "reject", "escalate"]
    risk_findings: list[str] = Field(default_factory=list)
    required_controls: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ResearchReport(BaseModel):
    """Structured research report produced by read-only research agents."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    report_id: str = Field(min_length=1)
    research_question: str = Field(min_length=1)
    source_agent: str = Field(min_length=1)
    sources_used: list[str] = Field(default_factory=list)
    market_context: dict[str, Any] = Field(default_factory=dict)
    candidate_ideas: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TradeProposal(BaseModel):
    """Agent-facing trade proposal view required by the firm plan."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    entry_type: Literal["market", "limit", "stop", "stop_limit"]
    requested_size: float | dict[str, Any]
    stop_loss: float | None = None
    take_profit: float | None = None
    max_spread: float | None = None
    max_slippage: float | None = None
    expected_risk: dict[str, Any] = Field(default_factory=dict)
    portfolio_impact: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    requires_risk_approval: bool = True

    @classmethod
    def from_canonical(cls, proposal: CanonicalTradeProposal) -> "TradeProposal":
        payload = proposal.payload
        return cls(
            strategy_id=proposal.strategy_scope_id or payload.source_hypothesis_id,
            symbol=payload.symbol,
            side=payload.direction,
            entry_type=str(payload.candidate_price_logic.get("entry_type") or "market"),
            requested_size=payload.proposed_size,
            stop_loss=payload.candidate_price_logic.get("stop_loss"),
            take_profit=payload.candidate_price_logic.get("take_profit"),
            max_spread=payload.operating_envelope.get("max_spread"),
            max_slippage=payload.operating_envelope.get("max_slippage"),
            expected_risk=payload.operating_envelope.get("expected_risk", {}),
            portfolio_impact=payload.operating_envelope.get("portfolio_impact", {}),
            requires_risk_approval=True,
        )


class RiskApproval(BaseModel):
    """Agent-facing view over deterministic risk approval decisions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    approval_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    approved: bool
    approval_token: str | None = None
    expires_at: datetime | None = None
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @classmethod
    def from_risk_decision(
        cls, decision: CanonicalRiskAssessmentDecision
    ) -> "RiskApproval":
        payload = decision.payload
        return cls(
            approval_id=payload.risk_decision_id,
            proposal_id=payload.proposal_id,
            approved=payload.decision in {"APPROVE", "APPROVE_WITH_LIMITS"},
            approval_token=payload.approval_token,
            expires_at=payload.freshness_expiry,
            constraints=[
                constraint.model_dump(mode="json")
                for constraint in payload.limit_constraints
            ],
            reasons=payload.reasons,
        )


class ExecutionRequest(BaseModel):
    """Agent-facing execution request view over canonical ExecutionIntent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    execution_request_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    risk_approval_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop", "stop_limit"]
    size: dict[str, Any]
    price_params: dict[str, Any] = Field(default_factory=dict)
    sl_tp_params: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)
    expires_at: datetime
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @classmethod
    def from_execution_intent(
        cls, intent: CanonicalExecutionIntent
    ) -> "ExecutionRequest":
        payload = intent.payload
        return cls(
            execution_request_id=payload.execution_intent_id,
            proposal_id=payload.proposal_id,
            risk_approval_id=payload.risk_decision_id,
            symbol=payload.symbol,
            side=payload.side,
            order_type=payload.order_type,
            size=payload.size,
            price_params=payload.price_params,
            sl_tp_params=payload.sl_tp_params,
            idempotency_key=payload.idempotency_key,
            expires_at=payload.expiry_time,
        )


class ExecutionResult(BaseModel):
    """Agent-facing execution result view over canonical ExecutionReceipt."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    execution_result_id: str = Field(min_length=1)
    execution_request_id: str = Field(min_length=1)
    broker: str = Field(min_length=1)
    status: str = Field(min_length=1)
    broker_order_id: str | None = None
    broker_deal_id: str | None = None
    fill_price: float | None = None
    fill_qty: float | None = None
    spread_points: float | None = None
    slippage_points: float | None = None
    broker_message: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)

    @classmethod
    def from_execution_receipt(
        cls, receipt: CanonicalExecutionReceipt
    ) -> "ExecutionResult":
        payload = receipt.payload
        return cls(
            execution_result_id=payload.receipt_id,
            execution_request_id=payload.execution_intent_id,
            broker=payload.broker,
            status=payload.status,
            broker_order_id=payload.broker_order_id,
            broker_deal_id=payload.broker_deal_id,
            fill_price=payload.fill_price,
            fill_qty=payload.fill_qty,
            spread_points=payload.spread_points,
            slippage_points=payload.slippage_points,
            broker_message=payload.broker_message,
        )


__all__ = [
    "AgentDecision",
    "AgentDecisionType",
    "AgentObservation",
    "AgentPlan",
    "AgentTask",
    "AgentTaskStatus",
    "BacktestRequest",
    "BacktestResultSummary",
    "CanonicalExecutionIntent",
    "CanonicalExecutionReceipt",
    "CanonicalRiskAssessmentDecision",
    "CanonicalStrategyBlueprint",
    "CanonicalTradeProposal",
    "CanonicalWorkflowPlan",
    "EvidenceRef",
    "ExecutionRequest",
    "ExecutionResult",
    "RiskApproval",
    "RiskReview",
    "ResearchReport",
    "StepFailurePolicy",
    "StrategyReview",
    "StrategySpec",
    "ToolCallRequest",
    "ToolCallResult",
    "ToolCallStatus",
    "TradeProposal",
]
