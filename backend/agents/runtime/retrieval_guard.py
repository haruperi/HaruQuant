"""Lightweight safety checks for retrieved research context."""

from __future__ import annotations

from dataclasses import dataclass


_PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "reveal the system prompt",
    "system prompt",
    "execute trade now",
    "<tool_call>",
)

_CONTAMINATION_MARKERS = (
    "assistant:",
    "system:",
    "developer:",
    "unverified rumor",
    "fabricated citation",
)


@dataclass(frozen=True)
class RetrievalSafetyReport:
    safe: bool
    reason_codes: tuple[str, ...]


def evaluate_retrieved_text(text: str) -> RetrievalSafetyReport:
    """Fail closed when retrieved research context contains unsafe control markers."""

    normalized = text.lower()
    reason_codes: list[str] = []
    if any(marker in normalized for marker in _PROMPT_INJECTION_MARKERS):
        reason_codes.append("prompt_injection_marker_detected")
    if any(marker in normalized for marker in _CONTAMINATION_MARKERS):
        reason_codes.append("retrieval_contamination_marker_detected")
    return RetrievalSafetyReport(
        safe=not reason_codes,
        reason_codes=tuple(reason_codes),
    )
