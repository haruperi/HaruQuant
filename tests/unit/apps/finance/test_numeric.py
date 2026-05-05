import numpy as np

from haruquant.analytics import drawdowns, ratios


def test_core_trade_metrics_use_shared_array_math():
    values = np.array([1.0, -0.5, 0.5, -1.0], dtype=float)

    assert ratios.expectancy(values) == 0.0
    assert ratios.win_rate_fraction(values) == 0.5
    assert ratios.profit_factor(values) == 1.0
    assert ratios.payoff_ratio(values) == 1.0


def test_max_drawdown_and_recovery_factor_from_returns():
    returns = np.array([0.10, -0.20, 0.05], dtype=float)

    assert np.isclose(drawdowns.max_drawdown(returns), -0.20)
    assert np.isclose(drawdowns.recovery_factor(returns), -0.076 / 0.20, atol=1e-9)
