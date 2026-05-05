"""Structured exchange schemas for the HaruQuant agentic firm."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevel = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal["pending", "running", "blocked", "completed", "failed", "cancelled"]
DecisionVerdict = Literal["approve", "approve_with_limits", "reject", "needs_review"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FirmModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceRef(FirmModel):
    evidence_id: str
    evidence_type: str
    uri: str | None = None
    summary: str | None = None
    checksum: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class AgentTask(FirmModel):
    task_id: str
    parent_id: str | None = None
    agent_name: str
    task_type: str
    status: TaskStatus = "pending"
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = "low"
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_state: dict[str, Any] | None = None


class AgentObservation(FirmModel):
    observation_id: str
    task_id: str | None = None
    agent_name: str
    observation_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=utc_now)


class AgentDecision(FirmModel):
    decision_id: str
    task_id: str | None = None
    agent_name: str
    decision_type: str
    verdict: DecisionVerdict
    rationale: str
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=utc_now)


class ToolCallRequest(FirmModel):
    tool_call_id: str
    task_id: str | None = None
    agent_name: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = "low"
    requires_audit_log: bool = True
    requires_human_approval: bool = False
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    requested_at: datetime = Field(default_factory=utc_now)


class ToolCallResult(FirmModel):
    tool_call_id: str
    tool_name: str
    status: Literal["success", "failed", "blocked"]
    output: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=utc_now)


class StrategySpec(FirmModel):
    strategy_name: str
    version: str = "0.1.0"
    market: str
    symbol: str
    timeframe: str
    data_requirements: list[str] = Field(default_factory=list)
    entry_logic: list[str] = Field(min_length=1)
    exit_logic: list[str] = Field(min_length=1)
    position_sizing: dict[str, Any]
    risk_assumptions: list[str] = Field(default_factory=list)
    cost_assumptions: list[str] = Field(default_factory=list)
    invalid_conditions: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)
    deployment_recommendation: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class StrategyReview(FirmModel):
    review_id: str
    strategy_id: str | None = None
    reviewer_agent: str
    verdict: DecisionVerdict
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=utc_now)


class BacktestRequest(FirmModel):
    request_id: str | None = None
    strategy_id: str
    symbol: str
    timeframe: str
    start: str | None = None
    end: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class BacktestResultSummary(FirmModel):
    run_id: str
    strategy_id: str | None = None
    status: Literal["success", "failed", "inconclusive"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class RiskReview(FirmModel):
    review_id: str
    subject_ref: str
    verdict: DecisionVerdict
    risk_level: RiskLevel
    reasons: list[str] = Field(min_length=1)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=utc_now)


class TradeProposal(FirmModel):
    strategy_id: str
    symbol: str
    side: Literal["buy", "sell"]
    entry_type: Literal["market", "limit", "stop"]
    requested_size: float = Field(gt=0)
    stop_loss: float | None = None
    take_profit: float | None = None
    max_spread: float | None = Field(default=None, ge=0)
    max_slippage: float | None = Field(default=None, ge=0)
    expected_risk: dict[str, Any] = Field(default_factory=dict)
    portfolio_impact: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    requires_risk_approval: bool = True


class RiskApproval(FirmModel):
    approval_id: str
    proposal_id: str
    decision: Literal["approved", "approved_with_limits", "rejected"]
    approved_by: str
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    approved_at: datetime = Field(default_factory=utc_now)


class ExecutionRequest(FirmModel):
    execution_request_id: str
    proposal_id: str
    risk_approval_id: str
    symbol: str
    side: Literal["buy", "sell"]
    size: float = Field(gt=0)
    order_type: Literal["market", "limit", "stop"]
    idempotency_key: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ExecutionResult(FirmModel):
    execution_result_id: str
    execution_request_id: str
    status: Literal["accepted", "filled", "partial", "rejected", "failed"]
    broker_order_id: str | None = None
    fill_price: float | None = None
    filled_size: float | None = None
    message: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=utc_now)


class ResearchReport(FirmModel):
    report_id: str
    source_agent: str
    agent_name: str | None = None
    topic: str
    summary: str
    research_question: str | None = None
    sources_used: list[str] = Field(default_factory=list)
    market_context: dict[str, Any] = Field(default_factory=dict)
    candidate_ideas: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class AgentArtifact(FirmModel):
    artifact_id: str
    artifact_type: str
    source_agent: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ConversationPlan(FirmModel):
    conversation_plan_id: str
    user_goal: str
    response_mode: str
    task_class: str
    model_tier: str
    response_style: str
    domain_focus: str | None = None
    rationale: str
    intent: str
    missing_inputs: list[str] = Field(default_factory=list)
    context_needed: list[str] = Field(default_factory=list)
    backend_tools_to_run: list[str] = Field(default_factory=list)
    attached_tools: list[str] = Field(default_factory=list)
    page_actions_to_plan: list[str] = Field(default_factory=list)
    artifact_expected: bool = False
    risk_level: RiskLevel = "low"
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    requires_audit_log: bool = True
    allowed_agents: list[str] = Field(default_factory=list)
    blocked_agents: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    failure_policy: dict[str, Any] = Field(default_factory=dict)
    needs_clarification: bool = False
    planner_source: str = "phase6_planner"

    @field_validator("user_goal", "rationale", "intent")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must not be empty")
        return value


AgentPlan = ConversationPlan


__all__ = [
    "AgentDecision",
    "AgentArtifact",
    "AgentObservation",
    "AgentPlan",
    "AgentTask",
    "BacktestRequest",
    "BacktestResultSummary",
    "ConversationPlan",
    "EvidenceRef",
    "ExecutionRequest",
    "ExecutionResult",
    "ResearchReport",
    "RiskApproval",
    "RiskReview",
    "StrategyReview",
    "StrategySpec",
    "ToolCallRequest",
    "ToolCallResult",
    "TradeProposal",
]
