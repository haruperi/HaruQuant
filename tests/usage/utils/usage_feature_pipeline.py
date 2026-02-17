"""Usage example for IP-13 feature pipeline (batch + streaming + graph)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.features.pipeline import FeaturePipeline, FeatureSpec


def build_sample_data(rows: int = 80) -> pd.DataFrame:
    idx = pd.date_range("2026-02-10", periods=rows, freq="15min", tz="UTC")
    close = np.linspace(1.1000, 1.1200, rows) + np.sin(np.linspace(0, 5, rows)) * 0.001
    data = pd.DataFrame(index=idx)
    data["close"] = close
    data["open"] = close - 0.0003
    data["high"] = close + 0.0006
    data["low"] = close - 0.0006
    data["volume"] = np.linspace(100, 200, rows)
    return data


def main() -> None:
    pipeline = FeaturePipeline(
        [
            FeatureSpec("sma", {"window": 20}),
            FeatureSpec("ema", {"span": 20}),
            FeatureSpec("rsi", {"period": 14}),
            FeatureSpec("atr", {"period": 14}),
            FeatureSpec("bbands", {"period": 20, "std_dev": 2.0}),
            FeatureSpec("adl"),
        ],
        pipeline_version="1.0.0",
    )

    bars = build_sample_data()

    # Batch
    batch = pipeline.compute_batch(bars)
    print("batch columns:", [c for c in batch.columns if c not in {"open", "high", "low", "close", "volume"}])
    print("batch last row:")
    print(batch.tail(1).T)

    # Streaming
    latest = {}
    for ts, row in bars.iterrows():
        latest = pipeline.compute_incremental(
            symbol="EURUSD",
            bar={
                "timestamp": ts,
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            },
        )
    print("streaming latest keys:", sorted(k for k in latest.keys() if k not in {"symbol", "timestamp"}))

    # Graph inspection
    graph = pipeline.inspect_graph()
    print("graph nodes:", len(graph["nodes"]))
    print("graph edges:", len(graph["edges"]))
    print("sample edges:", graph["edges"][:5])


if __name__ == "__main__":
    main()
