from __future__ import annotations

import pandas as pd

from haruquant.research import _compute_range_reversion_metrics


def _range_break_reentry_df() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=32, freq="h")
    close = (
        [1.1000] * 20
        + [1.1012, 1.1016, 1.1001, 1.1013, 1.1014, 1.1000, 1.1001, 1.1000, 1.1000, 1.1001, 1.1000, 1.1000]
    )
    open_prices = [close[0]] + close[:-1]
    high = [price + 0.0002 for price in close]
    low = [price - 0.0002 for price in close]
    return pd.DataFrame(
        {
            "Open": open_prices,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": [100] * len(close),
            "Spread": [10] * len(close),
        },
        index=idx,
    )


def test_range_breakout_metrics_use_prior_range_levels():
    metrics = _compute_range_reversion_metrics(
        _range_break_reentry_df(),
        symbol="EURUSD",
        close_col="Close",
        high_col="High",
        low_col="Low",
    )

    assert metrics["reentry_probability"] > 0.0
    assert metrics["breakout_follow_probability"] >= 0.0
    assert metrics["false_break_frequency"] >= 0.0
