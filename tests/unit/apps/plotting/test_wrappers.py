import pytest
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.wrappers import (
    plot_returns,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_rolling_sharpe,
    plot_yearly_returns,
    plot_daily_returns,
    plot_distribution
)

@pytest.fixture
def equity_curve():
    dates = pd.date_range("2024-01-01", periods=100)
    return pd.Series(np.linspace(10000, 11000, 100), index=dates)

@pytest.fixture
def benchmark_curve(equity_curve):
    return equity_curve * 0.9

class TestPlottingWrappers:
    def test_plot_returns(self, equity_curve, benchmark_curve):
        # Basic usage
        fig = plot_returns(equity_curve, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

        # With benchmark and savefig
        with patch("apps.plotting.wrappers.save_figure") as mock_save:
            fig = plot_returns(
                equity_curve, 
                benchmark=benchmark_curve, 
                savefig="test_returns.png",
                show=False,
                grayscale=True
            )
            mock_save.assert_called()
            plt.close(fig)

        # Test with numpy array input - patch underlying function to avoid date math issues
        with patch("apps.plotting.wrappers._plot_cumulative_returns") as mock_plot:
            fig = plot_returns(equity_curve.values, show=False)
            mock_plot.assert_called()
        plt.close(fig)

    def test_plot_drawdown(self, equity_curve):
        fig = plot_drawdown(equity_curve, show=False, title="My Drawdown")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

        # Ensure wrapper calls underlying function
        with patch("apps.plotting.wrappers._plot_drawdown") as mock_plot:
             plot_drawdown(equity_curve, show=False)
             mock_plot.assert_called()

    def test_plot_monthly_heatmap(self, equity_curve):
        # Need enough data for heatmap
        long_equity = pd.Series(
            np.linspace(10000, 12000, 365), 
            index=pd.date_range("2024-01-01", periods=365)
        )
        fig = plot_monthly_heatmap(long_equity, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
        
    def test_plot_rolling_sharpe(self, equity_curve):
        fig = plot_rolling_sharpe(equity_curve, window=20, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

        with patch("apps.plotting.wrappers._plot_rolling_sharpe") as mock_plot:
            plot_rolling_sharpe(equity_curve, show=False)
            mock_plot.assert_called()

    def test_plot_yearly_returns(self, equity_curve):
        # Ensure we have data spanning years
        long_equity = pd.Series(
            np.linspace(10000, 15000, 500), 
            index=pd.date_range("2023-01-01", periods=500)
        )
        fig = plot_yearly_returns(long_equity, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_daily_returns(self, equity_curve):
        fig = plot_daily_returns(equity_curve, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_distribution(self, equity_curve):
        fig = plot_distribution(equity_curve, show=False)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
