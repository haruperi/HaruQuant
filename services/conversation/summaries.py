"""Deterministic rolling summaries for durable CEO chat memory."""

from __future__ import annotations

from services.schemas.chat import ChatMessage


def build_rolling_summary(messages: list[ChatMessage], *, max_chars: int = 700) -> str:
    """Create a compact summary without relying on an LLM provider."""

    user_turns = [message.content.strip() for message in messages if message.role == "user"]
    assistant_turns = [message.content.strip() for message in messages if message.role == "assistant"]
    parts: list[str] = []
    if user_turns:
        parts.append(f"Operator asked about: {'; '.join(user_turns[-3:])}")
    if assistant_turns:
        parts.append(f"CEO responded with: {'; '.join(assistant_turns[-2:])}")
    summary = " | ".join(parts) or "No durable conversation content yet."
    return summary[:max_chars].rstrip()

