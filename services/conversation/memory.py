"""Durable memory facade for CEO chat conversations."""

from __future__ import annotations

from uuid import uuid4

from data.database.repositories.ai_chat_repository import AiChatRepository
from services.conversation.summaries import build_rolling_summary
from services.schemas.chat import ChatMemorySummary, ChatMessage, ChatPinnedFact


class ConversationMemoryService:
    """Keeps durable chat memory separate from ephemeral page context."""

    def __init__(self, repository: AiChatRepository) -> None:
        self.repository = repository

    def maybe_refresh_summary(
        self,
        *,
        thread_id: str,
        user_id: str,
        messages: list[ChatMessage],
        every_messages: int = 6,
    ) -> ChatMemorySummary | None:
        if len(messages) < every_messages or len(messages) % every_messages != 0:
            row = self.repository.get_latest_memory_summary(thread_id=thread_id, user_id=user_id)
            if row is None:
                return None
            return ChatMemorySummary(
                summary_text=row.summary_text,
                generated_at=row.created_at,
                source_message_count=row.source_message_count,
            )

        row = self.repository.create_memory_summary(
            summary_id=f"summary-{uuid4()}",
            thread_id=thread_id,
            user_id=user_id,
            summary_text=build_rolling_summary(messages),
            source_message_count=len(messages),
        )
        return ChatMemorySummary(
            summary_text=row.summary_text,
            generated_at=row.created_at,
            source_message_count=row.source_message_count,
        )

    def list_pinned_facts(self, *, thread_id: str, user_id: str) -> list[ChatPinnedFact]:
        return [
            ChatPinnedFact(key=row.fact_key, value=row.fact_value, source=row.source)
            for row in self.repository.list_pinned_facts(thread_id=thread_id, user_id=user_id)
        ]

