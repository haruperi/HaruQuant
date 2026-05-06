"""Conversation service for the canonical HaruQuant CEO chat."""

from __future__ import annotations

import json
from uuid import uuid4

from data.database.repositories.ai_chat_repository import (
    AiChatActionDraftRow,
    AiChatMessageRow,
    AiChatRepository,
    AiChatThreadRow,
)
from services.conversation.memory import ConversationMemoryService
from services.conversation.title import generate_thread_title
from services.schemas.chat import (
    ChatMemorySummary,
    ChatMessage,
    ChatResponseMetadata,
    ChatThread,
    ChatThreadDetail,
)


def _metadata_from_json(payload: str | None) -> ChatResponseMetadata | None:
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {}
    return ChatResponseMetadata(**data) if data else None


def _thread_from_row(row: AiChatThreadRow) -> ChatThread:
    return ChatThread(
        thread_id=row.thread_id,
        user_id=row.user_id,
        title=row.title,
        status=row.status,  # type: ignore[arg-type]
        retention_class=row.retention_class,  # type: ignore[arg-type]
        active_context_revision=row.active_context_revision,
        current_route=row.current_route,
        current_page_type=row.current_page_type,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_message_at=row.last_message_at,
    )


def _message_from_row(row: AiChatMessageRow) -> ChatMessage:
    try:
        tool_calls = json.loads(row.tool_calls_json or "[]")
    except json.JSONDecodeError:
        tool_calls = []
    return ChatMessage(
        message_id=row.message_id,
        thread_id=row.thread_id,
        role=row.role,  # type: ignore[arg-type]
        content=row.content,
        request_id=row.request_id,
        tool_calls=tool_calls if isinstance(tool_calls, list) else [],
        signal_proposal_id=row.signal_proposal_id,
        action_draft_id=row.action_draft_id,
        context_revision=row.context_revision,
        created_at=row.created_at,
        metadata=_metadata_from_json(row.metadata_json),
    )


class ConversationService:
    """Durable chat operations used by the UI API and CEO gateway."""

    def __init__(self, repository: AiChatRepository) -> None:
        self.repository = repository
        self.memory = ConversationMemoryService(repository)

    def create_thread(
        self,
        *,
        user_id: str,
        title: str | None = None,
        current_route: str | None = None,
        current_page_type: str | None = None,
        active_context_revision: str | None = None,
    ) -> ChatThreadDetail:
        row = self.repository.create_thread(
            thread_id=f"thread-{uuid4()}",
            user_id=user_id,
            title=title or "CEO conversation",
            current_route=current_route,
            current_page_type=current_page_type,
            active_context_revision=active_context_revision,
        )
        return self.get_thread(thread_id=row.thread_id, user_id=user_id)

    def list_threads(self, *, user_id: str, query: str | None = None, limit: int = 50) -> list[ChatThread]:
        threads = [_thread_from_row(row) for row in self.repository.list_threads(user_id=user_id, limit=limit)]
        if query:
            lowered = query.lower()
            threads = [thread for thread in threads if lowered in thread.title.lower()]
        return threads

    def get_thread(self, *, thread_id: str, user_id: str) -> ChatThreadDetail:
        row = self.repository.get_thread(thread_id, user_id=user_id)
        if row is None:
            raise LookupError(f"thread not found: {thread_id}")
        messages = [
            _message_from_row(message)
            for message in self.repository.list_messages(thread_id=thread_id, user_id=user_id, limit=500)
        ]
        summary_row = self.repository.get_latest_memory_summary(thread_id=thread_id, user_id=user_id)
        summary = (
            ChatMemorySummary(
                summary_text=summary_row.summary_text,
                generated_at=summary_row.created_at,
                source_message_count=summary_row.source_message_count,
            )
            if summary_row is not None
            else None
        )
        return ChatThreadDetail(
            **_thread_from_row(row).model_dump(),
            memory_summary=summary,
            pinned_facts=self.memory.list_pinned_facts(thread_id=thread_id, user_id=user_id),
            messages=messages,
        )

    def rename_thread(self, *, thread_id: str, user_id: str, title: str) -> ChatThreadDetail:
        self.repository.update_thread_title(thread_id=thread_id, user_id=user_id, title=title.strip() or "CEO conversation")
        return self.get_thread(thread_id=thread_id, user_id=user_id)

    def delete_thread(self, *, thread_id: str, user_id: str) -> bool:
        return self.repository.soft_delete_thread(thread_id=thread_id, user_id=user_id)

    def update_context(
        self,
        *,
        thread_id: str,
        user_id: str,
        current_route: str | None,
        current_page_type: str | None,
        active_context_revision: str | None,
    ) -> ChatThreadDetail:
        self.repository.update_thread_context(
            thread_id=thread_id,
            user_id=user_id,
            current_route=current_route,
            current_page_type=current_page_type,
            active_context_revision=active_context_revision,
        )
        return self.get_thread(thread_id=thread_id, user_id=user_id)

    def add_message(
        self,
        *,
        thread_id: str,
        user_id: str,
        role: str,
        content: str,
        request_id: str | None = None,
        context_revision: str | None = None,
        tool_calls: list[str] | None = None,
        signal_proposal_id: str | None = None,
        action_draft_id: str | None = None,
        metadata: ChatResponseMetadata | dict[str, object] | None = None,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        if role == "user":
            thread = self.repository.get_thread(thread_id, user_id=user_id)
            if thread and thread.title == "CEO conversation":
                self.repository.update_thread_title(
                    thread_id=thread_id,
                    user_id=user_id,
                    title=generate_thread_title(content),
                )
        if isinstance(metadata, ChatResponseMetadata):
            metadata_json = metadata.model_dump_json()
        else:
            metadata_json = json.dumps(metadata or {})
        row = self.repository.add_message(
            message_id=f"msg-{uuid4()}",
            thread_id=thread_id,
            user_id=user_id,
            role=role,
            content=content,
            request_id=request_id,
            tool_calls_json=json.dumps(tool_calls or []),
            signal_proposal_id=signal_proposal_id,
            action_draft_id=action_draft_id,
            context_revision=context_revision,
            latency_ms=latency_ms,
            metadata_json=metadata_json,
        )
        messages = [
            _message_from_row(message)
            for message in self.repository.list_messages(thread_id=thread_id, user_id=user_id, limit=500)
        ]
        self.memory.maybe_refresh_summary(thread_id=thread_id, user_id=user_id, messages=messages)
        return _message_from_row(row)

    def export_thread(self, *, thread_id: str, user_id: str, format: str = "markdown") -> str:
        detail = self.get_thread(thread_id=thread_id, user_id=user_id)
        if format == "json":
            return detail.model_dump_json(indent=2)
        lines = [f"# {detail.title}", ""]
        for message in detail.messages:
            lines.extend([f"## {message.role.title()}", message.content, ""])
        return "\n".join(lines)

    def create_action_draft(
        self,
        *,
        thread_id: str,
        user_id: str,
        request_id: str | None,
        draft_type: str,
        title: str,
        description: str,
        payload: dict[str, object],
        risk_precheck_status: str = "not_required",
        risk_precheck_notes: str = "Draft only. No side effect has been executed.",
    ) -> AiChatActionDraftRow:
        return self.repository.create_action_draft(
            draft_id=f"draft-{uuid4()}",
            thread_id=thread_id,
            user_id=user_id,
            request_id=request_id,
            draft_type=draft_type,
            title=title,
            description=description,
            payload_json=json.dumps(payload),
            risk_precheck_status=risk_precheck_status,
            risk_precheck_notes=risk_precheck_notes,
            requires_human_approval=True,
        )

