"""Stale-state detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.common.logger import logger
from backend.common import Clock, SystemClock
from backend.common.time_utils import evaluate_freshness


@dataclass(frozen=True)
class StaleStateDetection:
    """Result of stale-state monitoring."""

    stale: bool
    severity: str
    reason_code: str


def detect_stale_state(
    *,
    observed_at: datetime,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> StaleStateDetection:
    """Escalate stale snapshots into incident-grade monitoring signals."""

    freshness = evaluate_freshness(
        observed_at,
        max_age_seconds=max_age_seconds,
        clock=clock or SystemClock(),
    )
    if freshness.is_stale:
        return StaleStateDetection(
            stale=True,
            severity="critical",
            reason_code="stale_state_detected",
        )
    return StaleStateDetection(
        stale=False,
        severity="info",
        reason_code="state_fresh",
    )
