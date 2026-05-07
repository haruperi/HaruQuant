"""Shared tracing helpers for HaruQuant agents."""

from __future__ import annotations

from uuid import uuid4


def new_trace_id(prefix: str = "trace") -> str:
    return f"{prefix}-{uuid4()}"


__all__ = ["new_trace_id"]
