"""Conversation title helpers for CEO chat threads."""

from __future__ import annotations


def generate_thread_title(prompt: str, *, fallback: str = "CEO conversation") -> str:
    cleaned = " ".join(prompt.strip().split())
    if not cleaned:
        return fallback
    title = cleaned[:64].rstrip(" .,;:")
    if len(cleaned) > len(title):
        title += "..."
    return title

