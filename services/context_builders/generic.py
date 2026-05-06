"""Generic fallback page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_generic_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="generic",
        summary_bullets=["Generic HaruQuant page context. Page-specific builder unavailable; using compact visible state."],
    )

