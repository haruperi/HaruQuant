from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Span:
    span_id: str | None = None
    parent_span_id: str | None = None
    trace_id: str | None = None
    name: str | None = None
    duration_ms: float | None = None
    status: str | None = None
