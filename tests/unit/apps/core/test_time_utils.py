from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.core.time_utils import FixedClock, SystemClock, evaluate_freshness, is_stale


UTC = timezone.utc


def test_system_clock_returns_utc_datetime():
    value = SystemClock().now()

    assert isinstance(value, datetime)
    assert value.tzinfo == UTC


def test_evaluate_freshness_reports_fresh_window():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 20, tzinfo=UTC))

    window = evaluate_freshness(observed, max_age_seconds=30, clock=clock)

    assert window.age_seconds == 20.0
    assert window.is_fresh is True
    assert window.is_stale is False
    assert window.expires_at == observed + timedelta(seconds=30)


def test_is_stale_returns_true_when_window_expired():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 1, tzinfo=UTC))

    assert is_stale(observed, max_age_seconds=30, clock=clock) is True


def test_evaluate_freshness_rejects_negative_ttl():
    with pytest.raises(ValueError):
        evaluate_freshness(
            datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            max_age_seconds=-1,
        )
