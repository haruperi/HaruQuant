"""Canonical schemas for the HaruQuant CEO chat channel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ChatModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ChatRole = Literal["system", "user", "assistant", "tool"]
ChatThreadStatus = Literal["active", "archived", "deleted", "purged"]
ChatRetentionClass = Literal["standard", "ephemeral", "regulated", "legal_hold"]
ChatPageType = Literal[
    "dashboard",
    "strategy_detail",
    "backtest_detail",
    "optimization_detail",
    "portfolio_risk",
    "live_trading",
    "data_workspace",
    "operator_workflow",
    "generic",
]


class ChatEntityRef(ChatModel):
    type: str
    id: str
    label: str | None = None


class PageContext(ChatModel):
    context_schema_version: str = "page_context.v1"
    route: str = "/"
    page_type: ChatPageType = "generic"
    page_title: str | None = None
    entity_refs: list[ChatEntityRef] = Field(default_factory=list)
    context_revision: str = Field(default_factory=lambda: f"ctx-{utc_now_iso()}")
    generated_at: str = Field(default_factory=utc_now_iso)
    freshness: dict[str, Any] = Field(default_factory=dict)
    authority: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatThread(ChatModel):
    thread_id: str
    user_id: str
    title: str
    status: ChatThreadStatus = "active"
    retention_class: ChatRetentionClass = "standard"
    created_at: str
    updated_at: str
    last_message_at: str | None = None
    active_context_revision: str | None = None
    current_route: str | None = None
    current_page_type: ChatPageType | None = None
    archived_at: str | None = None
    deleted_at: str | None = None
    purged_at: str | None = None
    retention_expires_at: str | None = None
    purge_after: str | None = None
    legal_hold_until: str | None = None
    legal_hold_reason: str | None = None


class ChatLifecycleAuditEvent(ChatModel):
    event_id: str
    thread_id: str
    user_id: str
    actor_id: str
    action: str
    from_status: str | None = None
    to_status: str | None = None
    from_retention_class: str | None = None
    to_retention_class: str | None = None
    reason: str
    metadata_json: str = "{}"
    created_at: str


class ChatRetentionPolicyDetail(ChatModel):
    thread: ChatThread
    audit_events: list[ChatLifecycleAuditEvent] = Field(default_factory=list)


class ChatResponseMetadata(ChatModel):
    request_id: str | None = None
    response_mode: str | None = None
    response_style: str | None = None
    task_class: str | None = None
    domain_focus: str | None = None
    answer_mode: str | None = None
    generation_source: str | None = None
    provider_name: str | None = None
    model: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    conversation_plan_id: str | None = None
    clarification_required: bool = False
    active_topic: str | None = None
    specialist_agents_used: list[str] = Field(default_factory=list)
    specialist_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    cost_policy: dict[str, Any] = Field(default_factory=dict)
    attached_tools: list[dict[str, Any]] = Field(default_factory=list)
    ceo_memo: dict[str, Any] = Field(default_factory=dict)
    planner: dict[str, Any] = Field(default_factory=dict)
    page_context: dict[str, Any] = Field(default_factory=dict)
    audit: dict[str, Any] = Field(default_factory=dict)


class ChatRouteDecision(ChatModel):
    intent: str
    task_class: str
    response_mode: str
    response_style: str
    domain_focus: str
    route_mode: str
    requires_tools: bool = False
    model_policy_key: str = "plain_answer"
    structured_schema: str | None = None


class ChatPromptLayerLog(ChatModel):
    name: str
    authority: str
    included: bool
    char_count: int = 0
    token_estimate: int = 0
    summary: str | None = None


class ChatPromptCompositionLog(ChatModel):
    schema_version: str = "prompt_composition.v1"
    request_id: str
    route: ChatRouteDecision
    layers: list[ChatPromptLayerLog] = Field(default_factory=list)
    message_count: int = 0
    token_estimate: int = 0
    truncated: bool = False


class ChatStructuredResponseSchema(ChatModel):
    schema_name: str
    response_mode: str
    json_schema: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(ChatModel):
    message_id: str
    thread_id: str
    role: ChatRole
    content: str
    created_at: str
    request_id: str | None = None
    tool_calls: list[str] = Field(default_factory=list)
    signal_proposal_id: str | None = None
    action_draft_id: str | None = None
    context_revision: str | None = None
    metadata: ChatResponseMetadata | None = None


class ChatMemorySummary(ChatModel):
    summary_text: str
    generated_at: str
    source_message_count: int


class ChatPinnedFact(ChatModel):
    key: str
    value: str
    source: str


class ChatThreadDetail(ChatThread):
    memory_summary: ChatMemorySummary | None = None
    pinned_facts: list[ChatPinnedFact] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatToolDefinition(ChatModel):
    tool_id: str
    display_name: str
    description: str
    capability_type: str
    authority_band: str
    side_effect_policy: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_context: list[str] = Field(default_factory=list)
    allowed_backend_tools: list[str] = Field(default_factory=list)
    allowed_specialist_agents: list[str] = Field(default_factory=list)
    artifact_type: str | None = None
    required_user_ack: bool = False


class ChatTurnRequest(ChatModel):
    prompt: str
    request_id: str | None = None
    include_debug: bool = False
    context_route: str | None = None
    context_page_title: str | None = None
    context_session_id: int | None = None
    context_symbol: str | None = None
    context_timeframe: str | None = None
    context_dom: dict[str, Any] | None = None
    context_page_intelligence: dict[str, Any] | None = None
    attached_tools: list[str] = Field(default_factory=list)


class ChatTurnResult(ChatModel):
    thread: ChatThreadDetail
    user_message: ChatMessage | None = None
    assistant_message: ChatMessage
    metadata: ChatResponseMetadata
