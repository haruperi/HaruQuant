from __future__ import annotations

import numpy as np
import pandas as pd

from apps.features.pipeline import FeaturePipeline, FeatureSpec


def _sample_ohlcv(rows: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2026-02-01", periods=rows, freq="15min", tz="UTC")
    base = np.linspace(1.10, 1.16, rows)
    wave = np.sin(np.linspace(0, 8, rows)) * 0.002
    close = base + wave
    open_ = close - 0.0004
    high = close + 0.0008
    low = close - 0.0008
    volume = np.linspace(100, 220, rows)
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


def _build_pipeline() -> FeaturePipeline:
    return FeaturePipeline(
        [
            FeatureSpec("sma", {"window": 20}),
            FeatureSpec("ema", {"span": 20}),
            FeatureSpec("rsi", {"period": 14}),
            FeatureSpec("atr", {"period": 14}),
            FeatureSpec("bbands", {"period": 20, "std_dev": 2.0}),
            FeatureSpec("adl"),
        ],
        pipeline_version="1.0.0",
        max_buffer_bars=500,
    )


def test_feature_pipeline_batch_computes_expected_columns() -> None:
    pipeline = _build_pipeline()
    data = _sample_ohlcv()
    out = pipeline.compute_batch(data)

    expected = {
        "sma_20",
        "ema_20",
        "rsi_14",
        "atr_14",
        "bb_upper_20_2",
        "bb_middle_20_2",
        "bb_lower_20_2",
        "adl",
    }
    assert expected.issubset(set(out.columns))
    assert len(out) == len(data)


def test_feature_pipeline_streaming_matches_batch_last_row() -> None:
    pipeline = _build_pipeline()
    data = _sample_ohlcv()
    batch = pipeline.compute_batch(data)

    latest = {}
    for ts, row in data.iterrows():
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

    compare_cols = [
        "sma_20",
        "ema_20",
        "rsi_14",
        "atr_14",
        "bb_upper_20_2",
        "bb_middle_20_2",
        "bb_lower_20_2",
        "adl",
    ]
    last_batch = batch.iloc[-1]
    for col in compare_cols:
        a = float(latest[col])
        b = float(last_batch[col])
        assert abs(a - b) < 1e-12


def test_feature_pipeline_graph_is_inspectable() -> None:
    pipeline = _build_pipeline()
    graph = pipeline.inspect_graph()
    nodes = set(graph["nodes"])
    edges = graph["edges"]

    assert "sma_20" in nodes
    assert "atr_14" in nodes
    assert "adl" in nodes
    assert any(e["from"] == "close" and e["to"] == "sma_20" for e in edges)
    assert any(e["from"] == "volume" and e["to"] == "adl" for e in edges)
