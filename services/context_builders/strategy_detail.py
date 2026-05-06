"""Strategy detail page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_strategy_detail_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="strategy_detail",
        summary_bullets=["Strategy detail context for hypothesis, parameters, indicators, versions, and validation state."],
    )

