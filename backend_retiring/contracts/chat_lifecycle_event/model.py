"""ChatLifecycleEvent canonical contract models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend_retiring.contracts.common import CanonicalEnvelope, Originator
from backend_retiring.contracts.page_context_packet.model import PageType


EventType = Literal[
    "chat.request.received",
    "chat.context.assembled",
    "chat.memory.loaded",
    "chat.route.selected",
    "chat.stream.started",
    "chat.stream.chunk",
    "chat.stream.completed",
    "chat.message.persisted",
    "chat.tool.called",
    "chat.tool.completed",
    "chat.tool.failed",
    "chat.policy.blocked",
    "chat.action.draft_created",
    "chat.action.approval_requested",
    "chat.action.approved",
    "chat.action.rejected",
    "chat.error",
]


class ChatLifecycleEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    event_version: str = "1.0.0"
    request_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    message_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    route: str | None = None
    page_type: PageType | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ChatLifecycleEvent(CanonicalEnvelope):
    """Canonical envelope specialization for chatbot lifecycle events."""

    contract_type: Literal["ChatLifecycleEvent"] = "ChatLifecycleEvent"
    payload: ChatLifecycleEventPayload


__all__ = [
    "ChatLifecycleEvent",
    "ChatLifecycleEventPayload",
    "EventType",
    "Originator",
]
