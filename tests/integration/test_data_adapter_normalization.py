"""Integration tests for MT5 ZeroMQ adapter with real local sockets."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any

import pandas as pd
import pytest

from apps.adapters.dukascopy_adapter import DukascopyHistoricalAdapter
from apps.adapters.mt5_zmq_adapter import MT5ZmqAdapter
from apps.adapters.pipeline import DataNormalizationPipeline

try:
    import zmq  # type: ignore

    HAVE_ZMQ = True
except Exception:
    HAVE_ZMQ = False
    zmq = None  # type: ignore


def _publish_messages(endpoint: str, messages: list[dict[str, Any]], delay_s: float = 0.05) -> None:
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.PUB)
    sock.setsockopt(zmq.LINGER, 0)
    sock.bind(endpoint)
    try:
        time.sleep(0.2)  # allow SUB side to connect/subscribe
        for msg in messages:
            topic = f"{msg['type']}.{msg.get('symbol', '')}".strip(".")
            payload = [
                topic.encode("utf-8"),
                json.dumps(msg, separators=(",", ":")).encode("utf-8"),
            ]
            # Send twice to reduce PUB/SUB startup loss during test handshakes.
            sock.send_multipart(payload)
            time.sleep(delay_s)
            sock.send_multipart(payload)
            time.sleep(delay_s)
    finally:
        sock.close(0)


@pytest.mark.skipif(not HAVE_ZMQ, reason="pyzmq is not installed")
def test_mt5_zmq_adapter_receives_and_normalizes_tick_and_bar():
    endpoint = "tcp://127.0.0.1:55781"
    messages = [
        {
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "type": "tick",
            "symbol": "EURUSD",
            "event_time_utc": "2026-02-17T12:00:00Z",
            "sequence": 1,
            "source": "demo-account",
            "bid": 1.1010,
            "ask": 1.1012,
            "volume": 100.0,
        },
        {
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "type": "bar",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "event_time_utc": "2026-02-17T12:01:00Z",
            "sequence": 2,
            "source": "demo-account",
            "open": 1.1010,
            "high": 1.1015,
            "low": 1.1008,
            "close": 1.1012,
            "volume": 250.0,
        },
    ]
    pub_thread = threading.Thread(target=_publish_messages, args=(endpoint, messages), daemon=True)
    pub_thread.start()

    adapter = MT5ZmqAdapter(endpoint=endpoint, topics=["tick.", "bar."], recv_timeout_ms=500)
    adapter.start()
    try:
        records = adapter.ingest(expected_count=4)
    finally:
        adapter.stop()
    pub_thread.join(timeout=2.0)

    assert len(records) == 4
    assert all(r["symbol"] == "EURUSD" for r in records)
    assert any("bid" in r and r["bid"] == pytest.approx(1.1010) for r in records)
    assert any("timeframe" in r and r["timeframe"] == "M1" and r["close"] == pytest.approx(1.1012) for r in records)


@pytest.mark.skipif(not HAVE_ZMQ, reason="pyzmq is not installed")
def test_mt5_zmq_adapter_progress_callback_reports_real_progress():
    endpoint = "tcp://127.0.0.1:55782"
    messages = [
        {
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "type": "tick",
            "symbol": "GBPUSD",
            "event_time_utc": "2026-02-17T12:00:00Z",
            "sequence": i,
            "bid": 1.2600 + i * 0.0001,
            "ask": 1.2602 + i * 0.0001,
            "volume": 10.0 + i,
        }
        for i in range(1, 4)
    ]
    pub_thread = threading.Thread(target=_publish_messages, args=(endpoint, messages), daemon=True)
    pub_thread.start()

    progress: list[tuple[int, int, float]] = []
    adapter = MT5ZmqAdapter(endpoint=endpoint, topics=["tick."], recv_timeout_ms=500)
    adapter.start()
    try:
        _ = adapter.ingest(expected_count=3, progress_callback=lambda done, total, pct: progress.append((done, total, pct)))
    finally:
        adapter.stop()
    pub_thread.join(timeout=2.0)

    assert progress
    assert progress[0][0] == 1
    assert progress[-1][0] == 3
    assert progress[-1][1] == 3
    assert progress[-1][2] == pytest.approx(100.0)


def test_dukascopy_adapter_normalizes_historical_with_progress():
    idx = pd.to_datetime(
        [
            "2026-02-17T12:00:00Z",
            "2026-02-17T12:01:00Z",
            "2026-02-17T12:02:00Z",
        ],
        utc=True,
    )
    fake_df = pd.DataFrame(
        {
            "open": [1.1000, 1.1001, 1.1002],
            "high": [1.1005, 1.1006, 1.1007],
            "low": [1.0998, 1.0999, 1.1000],
            "close": [1.1002, 1.1003, 1.1004],
            "volume": [100.0, 110.0, 120.0],
        },
        index=idx,
    )

    def fake_fetcher(**kwargs):
        assert kwargs["instrument"] == "EURUSD"
        return fake_df

    adapter = DukascopyHistoricalAdapter(fetcher=fake_fetcher)
    progress: list[tuple[int, int, float]] = []
    records = adapter.fetch_historical(
        symbol="EURUSD",
        timeframe="M1",
        start=datetime(2026, 2, 17, 12, 0, 0),
        end=datetime(2026, 2, 17, 12, 3, 0),
        progress_callback=lambda done, total, pct: progress.append((done, total, pct)),
    )

    assert len(records) == 3
    assert records[0]["provider"] == "dukascopy"
    assert records[0]["symbol"] == "EURUSD"
    assert records[-1]["close"] == pytest.approx(1.1004)
    assert progress[-1] == (3, 3, 100.0)


def test_pipeline_ingest_dukascopy_historical():
    idx = pd.to_datetime(["2026-02-17T12:00:00Z"], utc=True)
    fake_df = pd.DataFrame(
        {
            "open": [1.2],
            "high": [1.3],
            "low": [1.1],
            "close": [1.25],
            "volume": [200.0],
        },
        index=idx,
    )

    adapter = DukascopyHistoricalAdapter(fetcher=lambda **_: fake_df)
    pipeline = DataNormalizationPipeline()
    records = pipeline.ingest_dukascopy_historical(
        adapter=adapter,
        symbol="GBPUSD",
        timeframe="M1",
        start=datetime(2026, 2, 17, 12, 0, 0),
        end=datetime(2026, 2, 17, 12, 1, 0),
    )

    assert len(records) == 1
    assert records[0]["provider"] == "dukascopy"
    assert records[0]["symbol"] == "GBPUSD"
