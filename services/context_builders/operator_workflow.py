"""Operator workflow page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_operator_workflow_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="operator_workflow",
        summary_bullets=["Operator workflow context for active tasks, evidence, approvals, incidents, and handoffs."],
    )

