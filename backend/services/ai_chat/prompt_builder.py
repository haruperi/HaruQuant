"""Prompt composition for the HaruQuant AI chat gateway."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.page_context_packet.model import PageContextPacket
from backend.services.ai_chat.models import ConversationThreadRecord


@dataclass(frozen=True)
class BuiltPrompt:
    system_prompt: str
    user_prompt: str
    debug: dict[str, object]


class ChatPromptBuilder:
    """Compose layered prompts from context, memory, and recent conversation."""

    def build(
        self,
        *,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        user_prompt: str,
        response_mode: str,
    ) -> BuiltPrompt:
        recent_messages = thread.messages[-6:]
        memory_summary = thread.memory_summary.summary_text if thread.memory_summary else "No memory summary yet."
        pinned_facts = [
            f"{fact.key}={fact.value} ({fact.source})"
            for fact in thread.pinned_facts[:6]
        ] or ["none"]

        system_prompt = "\n".join(
            [
                "You are the HaruQuant AI Copilot.",
                "Prioritize current validated HaruQuant state over earlier chat assumptions.",
                "Stay within read-only assistance. Do not claim any action was executed.",
                f"Response mode: {response_mode}",
                f"Current page type: {page_context.payload.page_type}",
                f"Current page headline: {page_context.payload.summary.headline}",
                f"Context authority: {page_context.payload.authority.trust_level}",
                f"Memory summary: {memory_summary}",
                f"Pinned facts: {'; '.join(pinned_facts)}",
            ]
        )

        transcript_lines = [
            f"{message.role.upper()}: {message.content}"
            for message in recent_messages
        ] or ["No recent messages."]
        page_bullets = page_context.payload.summary.bullets or ["none"]
        entity_refs = [
            f"{entity.type}:{entity.id}:{entity.label or ''}".rstrip(":")
            for entity in page_context.payload.entity_refs[:6]
        ] or ["none"]

        composed_user_prompt = "\n".join(
            [
                f"Current route: {page_context.payload.route}",
                f"Context revision: {page_context.payload.context_revision}",
                f"Page entities: {'; '.join(entity_refs)}",
                f"Page bullets: {'; '.join(page_bullets)}",
                "Recent conversation:",
                *transcript_lines,
                "User request:",
                user_prompt.strip(),
            ]
        )

        return BuiltPrompt(
            system_prompt=system_prompt,
            user_prompt=composed_user_prompt,
            debug={
                "page_type": page_context.payload.page_type,
                "context_revision": page_context.payload.context_revision,
                "response_mode": response_mode,
                "recent_message_count": len(recent_messages),
            },
        )
