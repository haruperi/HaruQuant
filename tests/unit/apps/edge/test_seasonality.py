import numpy as np
import pandas as pd

from haruquant.research import run_seasonality


def _sample_seasonality_df() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=24 * 5, freq="h")
    base = 1.1000 + np.linspace(0.0, 0.01, len(index))
    hours = index.hour
    session_boost = np.where((hours >= 7) & (hours < 13), 0.0015, 0.0)
    ranges = np.where((hours >= 7) & (hours < 13), 0.0020, 0.0007)
    open_ = base
    close = base + np.where((hours >= 7) & (hours < 13), 0.0008, -0.0002)
    high = np.maximum(open_, close) + ranges / 2
    low = np.minimum(open_, close) - ranges / 2
    volume = np.where((hours >= 7) & (hours < 13), 220, 80)
    spread = np.where((hours >= 7) & (hours < 13), 8, 18)
    high = high + session_boost
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
            "Spread": spread,
        },
        index=index,
    )


def test_run_seasonality_includes_session_and_opportunity_outputs():
    result = run_seasonality(
        _sample_seasonality_df(),
        symbol="EURUSD",
        timeframe="H1",
        point_size=0.00001,
        pip_size=0.0001,
        data_limit=10,
    )

    assert "session_summary" in result
    assert "session_high_low" in result
    assert "opportunity_windows" in result
    assert len(result["session_summary"]) == 7
    assert result["session_high_low"]["total_days"] > 0
    assert len(result["opportunity_windows"]["best_hours"]) == 5
    assert len(result["opportunity_windows"]["dead_hours"]) == 5
    assert any(row["session"] == "london" for row in result["session_summary"])
    assert any(row["session"] == "london_ny" for row in result["session_summary"])
