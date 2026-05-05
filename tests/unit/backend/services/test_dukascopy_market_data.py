from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from haruquant.utils import FixedClock
from haruquant.data import get_instrument, normalize_dukascopy_bars


def test_get_instrument_resolves_currency_pair() -> None:
    assert get_instrument("EURUSD") == "EUR/USD"
    assert get_instrument("EUR/USD") == "EUR/USD"


def test_normalize_dukascopy_bars_adds_standard_columns_and_freshness() -> None:
    observed_at = datetime(2026, 4, 12, 8, 0, tzinfo=UTC)
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-04-12T07:58:00Z", "2026-04-12T07:59:00Z"]
            ),
            "open": [1.1, 1.2],
            "high": [1.15, 1.25],
            "low": [1.05, 1.15],
            "close": [1.12, 1.22],
            "volume": [100.0, 200.0],
        }
    )

    snapshot = normalize_dukascopy_bars(
        raw,
        symbol="eurusd",
        timeframe="m1",
        observed_at=observed_at,
        max_age_seconds=60,
    )

    assert snapshot.symbol == "EURUSD"
    assert snapshot.timeframe == "M1"
    assert snapshot.row_count == 2
    assert list(snapshot.bars.columns) == ["open", "high", "low", "close", "volume", "spread"]
    assert snapshot.freshness(clock=FixedClock(observed_at + timedelta(seconds=30))).is_fresh
    assert snapshot.freshness(clock=FixedClock(observed_at + timedelta(seconds=61))).is_stale
    assert snapshot.to_payload()["source"] == "dukascopy"
