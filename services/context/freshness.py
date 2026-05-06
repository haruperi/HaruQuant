"""Freshness helpers for ephemeral page context."""

from __future__ import annotations

from datetime import datetime, timezone


def freshness_payload(*, source: str = "ui_page_context") -> dict[str, object]:
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "observed_at": observed_at,
        "staleness_seconds": 0,
        "source": source,
    }

