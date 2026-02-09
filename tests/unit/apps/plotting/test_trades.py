import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.trades import (
    _extract_durations_and_outcomes,
    _extract_scatter_data,
    _calculate_pl_streaks,
    _plot_trade_durations,
    _plot_trade_sizes,
    _plot_trade_scatter,
    _plot_win_loss_streaks
)

@pytest.fixture
def sample_trades():
    return [
        {"entry_bar": 0, "exit_bar": 10, "pl": 100, "pl_pct": 0.05, "size": 1.0},
        {"entry_bar": 15, "exit_bar": 20, "pl": -50, "pl_pct": -0.02, "size": -1.0},
        {"entry_bar": 25, "exit_bar": 40, "pl": 200, "pl_pct": 0.10, "size": 2.0},
        {"entry_bar": 45, "exit_bar": 50, "pl": -20, "pl_pct": -0.01, "size": -0.5}
    ]

@pytest.fixture
def streak_trades():
    return [
        {"pl": 10}, {"pl": 20}, # Win streak 2
        {"pl": -10}, # Loss streak 1
        {"pl": 30}, {"pl": 40}, {"pl": 50}, # Win streak 3
        {"pl": -20}, {"pl": -30} # Loss streak 2
    ]

class TestTradeExtraction:
    def test_extract_durations_and_outcomes(self, sample_trades):
        dur, out = _extract_durations_and_outcomes(sample_trades)
        assert len(dur) == 4
        assert dur == [10, 5, 15, 5]
        assert out == ["win", "loss", "win", "loss"]

    def test_extract_scatter_data(self, sample_trades):
        dur, pl, sz, dirs = _extract_scatter_data(sample_trades)
        assert len(dur) == 4
        assert len(pl) == 4
        assert len(sz) == 4
        assert len(dirs) == 4
        assert dirs[0] == "long"
        assert dirs[1] == "short"

    def test_calculate_pl_streaks(self, streak_trades):
        streaks = _calculate_pl_streaks(streak_trades)
        # Sequence: + + - + + + - -
        # Streaks: +2, -1, +3, -2
        assert streaks == [2, -1, 3, -2]

class TestTradePlots:
    def test_plot_trade_durations(self, sample_trades):
        fig, ax_res = plt.subplots()
        res = _plot_trade_durations(sample_trades, ax=ax_res)
        assert res is not None
        # Check for presence of histogram patches
        assert len(ax_res.patches) > 0
        plt.close(fig)

    def test_plot_trade_sizes(self, sample_trades):
        fig, ax_res = plt.subplots()
        res = _plot_trade_sizes(sample_trades, ax=ax_res)
        assert res is not None
        assert len(ax_res.patches) > 0
        plt.close(fig)

    def test_plot_trade_scatter(self, sample_trades):
        fig, ax_res = plt.subplots()
        res = _plot_trade_scatter(sample_trades, ax=ax_res)
        assert res is not None
        assert len(ax_res.collections) > 0
        plt.close(fig)

    def test_plot_win_loss_streaks(self, streak_trades):
        fig, ax_res = plt.subplots()
        res = _plot_win_loss_streaks(streak_trades, ax=ax_res)
        assert res is not None
        assert len(ax_res.patches) > 0
        plt.close(fig)

    def test_empty_trades_handling(self):
        fig, ax = plt.subplots()
        assert _plot_trade_durations([], ax=ax) is ax
        assert _plot_trade_sizes([], ax=ax) is ax
        assert _plot_trade_scatter([], ax=ax) is ax
        assert _plot_win_loss_streaks([], ax=ax) is ax
        plt.close(fig)
