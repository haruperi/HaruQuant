"""Live trading page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_live_trading_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="live_trading",
        summary_bullets=["Live trading context for positions, orders, broker state, kill switches, and execution guardrails."],
    )

