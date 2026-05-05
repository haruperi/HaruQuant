from __future__ import annotations

import json

import pandas as pd
import pytest

from services.data.features import (
    FeaturePipeline,
    FeatureSpec,
    dump_masked_research_json,
    enforce_time_split,
    mask_research_artifact,
    validate_no_lookahead_features,
)


def _bars(rows: int = 40) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="min", name="timestamp")
    close = pd.Series(range(100, 100 + rows), index=index, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": pd.Series(range(1000, 1000 + rows), index=index, dtype=float),
        },
        index=index,
    )


def test_feature_pipeline_batch_outputs_indicators_and_provenance() -> None:
    pipeline = FeaturePipeline(
        [
            FeatureSpec("sma", {"window": 3}),
            FeatureSpec("ema", {"span": 4}),
            FeatureSpec("rsi", {"period": 5}),
            FeatureSpec("atr", {"period": 6}),
            FeatureSpec("bbands", {"period": 7, "std_dev": 2.0}),
            FeatureSpec("adl"),
        ],
        pipeline_version="phase8-test",
        max_buffer_bars=25,
    )

    result = pipeline.compute_batch(_bars())

    assert {"sma_3", "ema_4", "rsi_5", "atr_6", "bb_upper_7_2", "adl"} <= set(result.columns)
    provenance = result.attrs["feature_provenance"]
    assert provenance["pipeline_version"] == "phase8-test"
    assert provenance["pipeline_fingerprint"] == pipeline.fingerprint()
    assert provenance["source_rows"] == 40
    assert provenance["source_start"] == "2026-01-01T00:00:00"
    assert provenance["source_end"] == "2026-01-01T00:39:00"


def test_feature_pipeline_incremental_outputs_fingerprint_and_graph() -> None:
    pipeline = FeaturePipeline([FeatureSpec("sma", {"window": 2})], max_buffer_bars=2)

    first = pipeline.compute_incremental(
        symbol="EURUSD",
        bar={"timestamp": "2026-01-01T00:00:00", "open": 1, "high": 2, "low": 0.5, "close": 1, "volume": 10},
    )
    second = pipeline.compute_incremental(
        symbol="EURUSD",
        bar={"timestamp": "2026-01-01T00:01:00", "open": 2, "high": 3, "low": 1.5, "close": 2, "volume": 11},
    )

    assert first["feature_pipeline_fingerprint"] == pipeline.fingerprint()
    assert second["sma_2"] == pytest.approx(1.5)
    assert second["feature_provenance"]["source_rows"] == 2
    assert pipeline.inspect_graph()["edges"] == [{"from": "close", "to": "sma_2"}]


def test_leakage_guard_detects_future_close_feature() -> None:
    data = _bars(12)
    data["future_feature"] = data["close"].shift(-1)

    valid, reason = validate_no_lookahead_features(data, feature_columns=["future_feature"])

    assert valid is False
    assert "lookahead detected" in reason


def test_time_split_enforces_chronology_and_gap() -> None:
    split = enforce_time_split(_bars(20), train_frac=0.5, val_frac=0.25, test_frac=0.25, min_gap=1)

    assert len(split.train) == 10
    assert len(split.validation) == 5
    assert len(split.test) == 3
    assert split.train.index.max() < split.validation.index.min()
    assert split.validation.index.max() < split.test.index.min()


def test_research_artifact_masking_redacts_sensitive_values() -> None:
    masked = mask_research_artifact({"api_key": "secret-123", "note": "token=abc123"})
    dumped = dump_masked_research_json({"password": "secret-123"})

    assert masked["api_key"] != "secret-123"
    assert "abc123" not in masked["note"]
    assert "secret-123" not in dumped
    assert json.loads(dumped)["password"] != "secret-123"
