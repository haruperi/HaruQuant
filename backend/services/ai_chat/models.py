"""Conversation, memory, and signal proposal models for the AI chatbot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.contracts.page_context_packet.model import PageType


ConversationRole = Literal["system", "user", "assistant", "tool"]
ThreadStatus = Literal["active", "archived", "deleted"]
RetentionClass = Literal["standard", "ephemeral", "legal_hold"]
SignalProposalStatus = Literal["draft", "watchlist", "review_queue"]
SignalDirection = Literal["long", "short", "neutral"]
ActionDraftType = Literal[
    "order_draft",
    "backtest_launch",
    "optimization_launch",
    "export_request",
    "simulation_request",
]
ActionDraftStatus = Literal["draft", "approval_requested", "approved", "rejected", "cancelled"]
RiskPrecheckStatus = Literal["passed", "blocked", "not_required"]


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at", "updated_at")
    @classmethod
    def _validate_action_dt(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


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
    "ConversationMessageRecord",
    "ConversationRole",
    "ConversationThreadRecord",
    "MemorySummary",
    "PinnedFact",
    "RiskPrecheckStatus",
    "RetentionClass",
    "SignalProposalRecord",
    "SignalProposalStatus",
    "ThreadStatus",
]
