"""Contract tests for canonical tick/bar normalization."""

from __future__ import annotations

import pandas as pd

from apps.adapters.normalization import (
    normalize_dukascopy_dataframe,
    normalize_mt5_bar,
    normalize_mt5_event,
    normalize_mt5_tick,
)


def test_tick_contract_normalization():
    out = normalize_mt5_tick(
        {
            "type": "tick",
            "symbol": "EURUSD",
            "event_time_utc": "2026-02-17T12:00:00Z",
            "bid": 1.1000,
            "ask": 1.1002,
            "volume": 100.0,
            "sequence": 10,
        }
    )
    assert out["provider"] == "mt5_ea"
    assert out["schema_version"] == "1.0"
    assert out["symbol"] == "EURUSD"
    assert out["bid"] == 1.1000
    assert out["ask"] == 1.1002
    assert out["sequence"] == 10


def test_bar_contract_normalization():
    out = normalize_mt5_bar(
        {
            "type": "bar",
            "symbol": "EURUSD",
            "timeframe": "M5",
            "event_time_utc": "2026-02-17T12:05:00Z",
            "open": 1.1,
            "high": 1.1010,
            "low": 1.0990,
            "close": 1.1005,
            "volume": 220.0,
            "sequence": 11,
        }
    )
    assert out["symbol"] == "EURUSD"
    assert out["timeframe"] == "M5"
    assert out["high"] == 1.1010
    assert out["low"] == 1.0990
    assert out["close"] == 1.1005


def test_event_dispatch_rejects_invalid_payload():
    normalized, error = normalize_mt5_event(
        {
            "type": "tick",
            "symbol": "EURUSD",
            "event_time_utc": "2026-02-17T12:00:00Z",
            "bid": 1.1003,
            "ask": 1.1001,  # invalid ask < bid
            "volume": 10.0,
        }
    )
    assert normalized is None
    assert error is not None
    assert "ask" in error.lower()


def test_dukascopy_dataframe_contract_normalization():
    idx = pd.to_datetime(["2026-02-17T12:00:00Z", "2026-02-17T12:01:00Z"], utc=True)
    df = pd.DataFrame(
        {
            "open": [1.10, 1.11],
            "high": [1.12, 1.13],
            "low": [1.09, 1.10],
            "close": [1.11, 1.12],
            "volume": [1000, 1100],
        },
        index=idx,
    )
    out = normalize_dukascopy_dataframe(df, symbol="EURUSD", timeframe="M1")
    assert len(out) == 2
    assert out[0]["provider"] == "dukascopy"
    assert out[0]["symbol"] == "EURUSD"
    assert out[0]["timeframe"] == "M1"
    assert out[0]["sequence"] == 1
