from __future__ import annotations

import numpy as np
import pandas as pd

from apps.features.leakage import mask_research_artifact, validate_no_lookahead_features


def _base_df(rows: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2026-02-01", periods=rows, freq="h", tz="UTC")
    close = np.linspace(1.10, 1.20, rows)
    df = pd.DataFrame({"close": close}, index=idx)
    return df


def test_validate_no_lookahead_features_passes_for_safe_feature() -> None:
    df = _base_df()
    df["feat_safe"] = df["close"].rolling(window=5, min_periods=1).mean()
    ok, msg = validate_no_lookahead_features(df, feature_columns=["feat_safe"])
    assert ok is True
    assert msg == "no lookahead detected"


def test_validate_no_lookahead_features_detects_future_leakage() -> None:
    df = _base_df()
    # Leaky feature intentionally uses future close at t+1.
    df["feat_leaky"] = df["close"].shift(-1)
    ok, msg = validate_no_lookahead_features(df, feature_columns=["feat_leaky"])
    assert ok is False
    assert "lookahead detected" in msg


def test_mask_research_artifact_redacts_sensitive_fields() -> None:
    payload = {
        "strategy": "Demo",
        "config": {"api_key": "secret-key-123", "username": "alice"},
        "notes": "password=abc123",
    }
    out = mask_research_artifact(payload)
    assert isinstance(out, dict)
    assert out["config"]["api_key"] == "***REDACTED***"
    assert "abc123" not in out["notes"]
