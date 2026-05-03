"""Conversation, memory, and signal proposal models for the AI chatbot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.contracts.page_context_packet.model import PageType


ConversationRole = Literal["system", "user", "assistant", "tool"]
ThreadStatus = Literal["active", "archived", "deleted"]
RetentionClass = Literal["standard", "ephemeral", "legal_hold"]
SignalProposalStatus = Literal["draft", "watchlist", "review_queue"]
SignalDirection = Literal["long", "short", "neutral"]
ConversationAnswerMode = Literal["direct_answer", "clarification", "governed_artifact"]
ActionDraftType = Literal[
    "order_draft",
    "backtest_launch",
    "optimization_launch",
    "export_request",
    "simulation_request",
]
ActionDraftStatus = Literal["draft", "approval_requested", "approved", "rejected", "cancelled"]
RiskPrecheckStatus = Literal["passed", "blocked", "not_required"]
ChatToolCapabilityType = Literal[
    "strategy_creation",
    "strategy_refinement",
    "backtest_analysis",
    "optimization_comparison",
    "risk_review",
    "signal_proposal",
    "page_operation",
    "knowledge_retrieval",
]
ChatToolSideEffectPolicy = Literal["read_only", "artifact_only", "approval_gate", "draft_action", "page_action_plan"]


class PinnedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    value: str = Field(min_length=1)
    source: str = Field(min_length=1)


class MemorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary_text: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_message_count: int = Field(ge=0, default=0)

    @field_validator("generated_at")
    @classmethod
    def _validate_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class SignalProposalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str | None = None
    title: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    direction: SignalDirection
    entry_logic: str = Field(min_length=1)
    exit_logic: str = Field(min_length=1)
    confidence: int = Field(ge=0, le=100)
    rationale: str = Field(min_length=1)
    risk_note: str = Field(min_length=1)
    status: SignalProposalStatus = "draft"
    watchlist_saved: bool = False
    review_queue_saved: bool = False
    non_executed_label: str = Field(min_length=1, default="non_executed_signal_proposal")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", "updated_at")
    @classmethod
    def _validate_signal_dt(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ActionDraftRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str | None = None
    draft_type: ActionDraftType
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    payload: dict = Field(default_factory=dict)
    risk_precheck_status: RiskPrecheckStatus = "not_required"
    risk_precheck_notes: str = Field(default="")
    approval_id: str | None = None
    status: ActionDraftStatus = "draft"
    requires_human_approval: bool = True
    side_effect_status: str = Field(min_length=1, default="not_executed")
    governed_workflow_id: str | None = None
    execution_intent_id: str | None = None
    execution_receipt_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", "updated_at")
    @classmethod
    def _validate_action_dt(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ConversationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_plan_id: str = Field(min_length=1)
    user_goal: str = Field(min_length=1)
    answer_mode: ConversationAnswerMode = "direct_answer"
    response_mode: str = Field(min_length=1)
    task_class: str = Field(min_length=1)
    model_tier: str = Field(min_length=1)
    response_style: str = Field(min_length=1)
    domain_focus: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    needs_clarification: bool = False
    clarification_question: str | None = None
    intent: str = Field(min_length=1, default="answer")
    missing_inputs: list[str] = Field(default_factory=list)
    context_needed: list[str] = Field(default_factory=list)
    backend_tools_to_run: list[str] = Field(default_factory=list)
    tools_to_run: list[str] = Field(default_factory=list)
    agents_to_consult: list[str] = Field(default_factory=list)
    attached_tools: list[str] = Field(default_factory=list)
    page_actions_to_plan: list[str] = Field(default_factory=list)
    artifact_expected: str | None = None
    risk_level: str = Field(min_length=1, default="read_only")
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    requires_audit_log: bool = True
    allowed_agents: list[str] = Field(default_factory=list)
    blocked_agents: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    failure_policy: dict[str, Any] = Field(default_factory=dict)
    planner_source: str = Field(min_length=1, default="deterministic")
    planner_confidence: float = Field(ge=0, le=1, default=1.0)


class ChatToolAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    capability_type: ChatToolCapabilityType
    authority_band: str = Field(min_length=1)
    side_effect_policy: ChatToolSideEffectPolicy
    system_prompt_fragment: str = Field(min_length=1)
    response_template: str | None = None
    allowed_backend_tools: list[str] = Field(default_factory=list)
    allowed_specialist_agents: list[str] = Field(default_factory=list)
    required_context: list[str] = Field(default_factory=list)
    artifact_type: str | None = None
    missing_context: list[str] = Field(default_factory=list)


class ConversationEntityState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    id: str = Field(min_length=1)
    label: str | None = None
    source: str = Field(min_length=1)


class ConversationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_topic: str = Field(min_length=1)
    active_entities: list[ConversationEntityState] = Field(default_factory=list)
    resolved_references: dict[str, str] = Field(default_factory=dict)
    unresolved_references: list[str] = Field(default_factory=list)
    user_preferences: dict[str, str] = Field(default_factory=dict)
    source_message_count: int = Field(ge=0, default=0)


class SpecialistAgentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str = Field(min_length=1)
    task_class: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    confidence: int = Field(ge=0, le=100, default=60)
    action_plan: dict[str, Any] | None = None
    strategy_artifact: dict[str, Any] | None = None


class ConversationThreadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: ThreadStatus = "active"
    retention_class: RetentionClass = "standard"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_message_at: datetime | None = None
    active_context_revision: str | None = None
    current_route: str | None = None
    current_page_type: PageType | None = None
    memory_summary: MemorySummary | None = None
    pinned_facts: list[PinnedFact] = Field(default_factory=list)
    messages: list["ConversationMessageRecord"] = Field(default_factory=list)

    @field_validator("created_at", "updated_at", "last_message_at")
    @classmethod
    def _validate_dt(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ConversationMessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    role: ConversationRole
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    signal_proposal_id: str | None = None
    action_draft_id: str | None = None
    context_revision: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


__all__ = [
    "ActionDraftRecord",
    "ActionDraftStatus",
    "ActionDraftType",
    "ConversationAnswerMode",
    "ConversationEntityState",
    "ConversationMessageRecord",
    "ConversationPlan",
    "ConversationRole",
    "ConversationState",
    "ConversationThreadRecord",
    "ChatToolAttachment",
    "ChatToolCapabilityType",
    "ChatToolSideEffectPolicy",
    "MemorySummary",
    "PinnedFact",
    "RiskPrecheckStatus",
    "RetentionClass",
    "SignalProposalRecord",
    "SignalProposalStatus",
    "SpecialistAgentArtifact",
    "ThreadStatus",
]
