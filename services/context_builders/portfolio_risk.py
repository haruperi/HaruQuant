"""Portfolio risk page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_portfolio_risk_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="portfolio_risk",
        summary_bullets=["Portfolio risk context for exposure, drawdown, concentration, limits, and risk decisions."],
    )

