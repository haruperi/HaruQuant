"""Dashboard page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_dashboard_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="dashboard",
        summary_bullets=["Dashboard overview context for portfolio, alerts, KPIs, and current workspace state."],
    )

