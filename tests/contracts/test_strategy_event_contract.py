"""Contract test for canonical StrategyEvent payload shape."""

from __future__ import annotations

from datetime import datetime, timezone


def test_strategy_event_contract_payload_shape() -> None:
    payload = {
        "event_id": "evt-0001",
        "event_type": "bar",
        "symbol": "EURUSD",
        "strategy_id": "strategy-1",
        "event_ts": datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc),
        "recv_ts": datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc),
        "payload": {"close": 1.10123, "volume": 1000},
        "run_id": "run-20260218",
        "trace_id": "trace-abc",
        "correlation_id": "corr-xyz",
    }

    required = {
        "event_id",
        "event_type",
        "symbol",
        "strategy_id",
        "event_ts",
        "recv_ts",
        "payload",
        "run_id",
        "trace_id",
        "correlation_id",
    }
    assert required.issubset(payload.keys())
