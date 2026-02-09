import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.performance import (
    _plot_equity_curve,
    _plot_cumulative_returns,
    _plot_pl,
    _plot_returns_distribution
)

@pytest.fixture
def equity_data():
    dates = pd.date_range("2024-01-01", periods=100)
    equity = pd.Series(np.linspace(10000, 11000, 100), index=dates)
    return equity

@pytest.fixture
def returns_data():
    return pd.Series(np.random.normal(0.001, 0.01, 100))

@pytest.fixture
def trade_data(equity_data):
    return [
        {"pl": 100, "exit_time": equity_data.index[10]},
        {"pl": -50, "exit_time": equity_data.index[20]},
        {"pl": 200, "exit_time": equity_data.index[30]}
    ]

class TestEquityCurve:
    def test_plot_equity_curve_matplotlib(self, equity_data):
        fig, ax = plt.subplots()
        _plot_equity_curve(ax, equity_data, smooth=True)
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_plot_equity_curve_benchmark(self, equity_data):
        fig, ax = plt.subplots()
        benchmark = equity_data * 0.9 # Sim benchmark
        _plot_equity_curve(ax, equity_data, benchmark=benchmark)
        assert len(ax.lines) >= 2 # Strategy and benchmark
        plt.close(fig)
        
    def test_plot_equity_empty(self):
        fig, ax = plt.subplots()
        with pytest.raises(ValueError, match="Equity series is empty"):
            _plot_equity_curve(ax, pd.Series(dtype=float))
        plt.close(fig)

    def test_plot_equity_bokeh(self, equity_data):
        with patch("apps.plotting.performance.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            _plot_equity_curve(mock_fig, equity_data, backend="bokeh")
            assert mock_fig.line.called

class TestCumulativeReturns:
    def test_plot_cumulative_returns_matplotlib(self, returns_data):
        fig, ax = plt.subplots()
        # Mock index since plot uses dates
        returns_data.index = pd.date_range("2024-01-01", periods=len(returns_data))
        _plot_cumulative_returns(ax, returns_data)
        assert len(ax.lines) > 0 # Main line + zero line
        plt.close(fig)

    def test_plot_cumulative_returns_start_at_100(self, returns_data):
        fig, ax = plt.subplots()
        returns_data.index = pd.date_range("2024-01-01", periods=len(returns_data))
        _plot_cumulative_returns(ax, returns_data, start_at_zero=False)
        plt.close(fig)

    def test_plot_cumulative_returns_bokeh(self, returns_data):
        with patch("apps.plotting.performance.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            returns_data.index = pd.date_range("2024-01-01", periods=len(returns_data))
            _plot_cumulative_returns(mock_fig, returns_data, backend="bokeh")
            assert mock_fig.line.called

class TestPLPlot:
    def test_plot_pl_matplotlib(self, trade_data):
        fig, ax = plt.subplots()
        _plot_pl(ax, trade_data)
        assert len(ax.patches) > 0 # Bars
        plt.close(fig)

    def test_plot_pl_bokeh(self, trade_data):
        with patch("apps.plotting.performance.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            _plot_pl(mock_fig, trade_data, backend="bokeh")
            assert mock_fig.vbar.called

class TestReturnsDistribution:
    def test_plot_returns_dist_matplotlib(self, returns_data):
        fig, ax = plt.subplots()
        _plot_returns_distribution(ax, returns_data)
        assert len(ax.patches) > 0 # Histogram
        assert len(ax.lines) > 0 # Normal curve/stats lines
        plt.close(fig)
