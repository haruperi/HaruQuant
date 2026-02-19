"""Usage example for IP-14 leakage prevention and split policy enforcement."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.features.leakage import (
    enforce_time_split,
    mask_research_artifact,
    validate_no_lookahead_features,
)


def build_data(rows: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2026-02-01", periods=rows, freq="15min", tz="UTC")
    close = np.linspace(1.1, 1.2, rows)
    df = pd.DataFrame({"close": close}, index=idx)
    df["feat_safe"] = df["close"].rolling(10, min_periods=1).mean()
    return df


def main() -> None:
    data = build_data()

    ok, msg = validate_no_lookahead_features(data, feature_columns=["feat_safe"])
    print("PIT validation:", ok, msg)

    split = enforce_time_split(
        data,
        train_frac=0.7,
        val_frac=0.15,
        test_frac=0.15,
        min_gap=2,
    )
    print("split sizes:", len(split.train), len(split.validation), len(split.test))
    print("split boundaries:")
    print("  train:", split.train.index[0], "->", split.train.index[-1])
    print("  val  :", split.validation.index[0], "->", split.validation.index[-1])
    print("  test :", split.test.index[0], "->", split.test.index[-1])

    artifact = {
        "run_id": "run-123",
        "config": {"api_key": "real-key", "user": "alice"},
        "notes": "password=abc123",
    }
    masked = mask_research_artifact(artifact)
    print("masked artifact:", masked)


if __name__ == "__main__":
    main()
