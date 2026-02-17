"""Usage examples for IP-09 data adapters and normalization pipeline."""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from apps.adapters.dukascopy_adapter import DukascopyHistoricalAdapter
    from apps.adapters.mt5_zmq_adapter import MT5ZmqAdapter
    from apps.adapters.pipeline import DataNormalizationPipeline
except Exception as exc:
    print(f"Adapter unavailable: {exc}")
    raise SystemExit(1)


def mt5_stream_example() -> None:
    print("--- MT5 ZMQ stream example ---")
    adapter = MT5ZmqAdapter(
        endpoint="tcp://127.0.0.1:55781",
        topics=["tick.", "bar.", "heartbeat", "status"],
        recv_timeout_ms=500,
    )
    adapter.start()
    try:
        print("Waiting for 3 canonical events from MT5 EA stream...")
        rows = adapter.ingest(
            expected_count=3,
            progress_callback=lambda done, total, pct: print(
                f"progress: {done}/{total} ({pct:.1f}%)"
            ),
        )
        for row in rows:
            print(row)
    finally:
        adapter.stop()


def dukascopy_historical_example() -> None:
    print("--- Dukascopy historical example (local fake fetcher) ---")

    idx = pd.to_datetime(
        ["2026-02-17T12:00:00Z", "2026-02-17T12:01:00Z", "2026-02-17T12:02:00Z"],
        utc=True,
    )
    fake_df = pd.DataFrame(
        {
            "open": [1.1000, 1.1002, 1.1003],
            "high": [1.1005, 1.1006, 1.1007],
            "low": [1.0998, 1.1000, 1.1001],
            "close": [1.1002, 1.1003, 1.1005],
            "volume": [100.0, 120.0, 140.0],
        },
        index=idx,
    )

    adapter = DukascopyHistoricalAdapter(fetcher=lambda **_: fake_df)
    pipeline = DataNormalizationPipeline()
    rows = pipeline.ingest_dukascopy_historical(
        adapter=adapter,
        symbol="EURUSD",
        timeframe="M1",
        start=datetime(2026, 2, 17, 12, 0, 0),
        end=datetime(2026, 2, 17, 12, 3, 0),
        progress_callback=lambda done, total, pct: print(
            f"historical progress: {done}/{total} ({pct:.1f}%)"
        ),
    )
    print(f"normalized bars: {len(rows)}")
    if rows:
        print(rows[0])


def main() -> None:
    # Requires live MT5 EA ZMQ publisher at tcp://127.0.0.1:55781.
    # Uncomment when publisher is running:
    # mt5_stream_example()
    dukascopy_historical_example()


if __name__ == "__main__":
    main()
