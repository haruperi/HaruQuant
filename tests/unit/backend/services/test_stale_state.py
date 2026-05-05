from __future__ import annotations

from datetime import datetime, timezone

from services.utils import FixedClock
from services.execution.monitoring.stale_state import detect_stale_state


def test_detect_stale_state_raises_incident_grade_signal() -> None:
    result = detect_stale_state(
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        max_age_seconds=5,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 7, tzinfo=timezone.utc)),
    )
    assert result.stale is True
    assert result.reason_code == "stale_state_detected"


def test_detect_stale_state_accepts_fresh_snapshot() -> None:
    result = detect_stale_state(
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        max_age_seconds=5,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 3, tzinfo=timezone.utc)),
    )
    assert result.stale is False
