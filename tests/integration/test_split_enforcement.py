from __future__ import annotations

import numpy as np
import pandas as pd

from apps.features.leakage import enforce_time_split


def _df(rows: int = 100) -> pd.DataFrame:
    idx = pd.date_range("2026-02-01", periods=rows, freq="15min", tz="UTC")
    close = np.linspace(1.1, 1.2, rows)
    return pd.DataFrame({"close": close}, index=idx)


def test_enforce_time_split_is_chronological_and_disjoint() -> None:
    data = _df(120)
    result = enforce_time_split(
        data,
        train_frac=0.6,
        val_frac=0.2,
        test_frac=0.2,
        min_gap=2,
    )

    assert len(result.train) > 0
    assert len(result.validation) > 0
    assert len(result.test) > 0

    assert result.train.index.max() < result.validation.index.min()
    assert result.validation.index.max() < result.test.index.min()


def test_enforce_time_split_rejects_invalid_fractions() -> None:
    data = _df(100)
    try:
        enforce_time_split(
            data,
            train_frac=0.7,
            val_frac=0.2,
            test_frac=0.2,
        )
        assert False, "expected ValueError for invalid fractions"
    except ValueError as exc:
        assert "sum to 1.0" in str(exc)
