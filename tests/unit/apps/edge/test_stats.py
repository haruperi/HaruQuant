import numpy as np

from backend.services.analytics import metrics


def test_edge_stats_compute_trade_metrics():
    r = np.array([1.0, -1.0, 2.0], dtype=float)
    mae = np.array([-0.5, -1.0, -0.25], dtype=float)
    mfe = np.array([1.5, 0.5, 2.5], dtype=float)

    summary = metrics.compute_trade_metrics(r, mae=mae, mfe=mfe)

    assert summary["n_trades"] == 3
    assert np.isclose(summary["expectancy"], 2.0 / 3.0)
    assert np.isclose(summary["win_rate"], 2.0 / 3.0)
    assert "kelly_criterion" in summary
    assert "edge_ratio" in summary
    assert "trade_efficiency" in summary


def test_kelly_criterion_from_numeric_series():
    values = np.array([2.0, 1.0, -1.0, -1.0], dtype=float)

    result = metrics.kelly_criterion(values)

    assert np.isclose(result, 1.0 / 6.0)
