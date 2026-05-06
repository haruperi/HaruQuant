"""Backtest detail page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_backtest_detail_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="backtest_detail",
        summary_bullets=["Backtest detail context for run settings, performance, trades, drawdown, and diagnostics."],
    )

