"""Data workspace page-context builder."""

from __future__ import annotations

from services.context_builders.base import build_compact_context
from services.schemas.chat import PageContext


def build_data_workspace_context(**kwargs: object) -> PageContext:
    return build_compact_context(
        **kwargs,  # type: ignore[arg-type]
        page_type="data_workspace",
        summary_bullets=["Data workspace context for datasets, imports, quality checks, schemas, and lineage."],
    )

