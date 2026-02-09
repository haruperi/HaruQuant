import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.summary import (
    plot_snapshot,
    _plot_metrics_table,
    _plot_yearly_returns,
    _plot_daily_returns,
    _format_metric_value
)

@pytest.fixture
def returns_data():
    dates = pd.date_range("2023-01-01", "2024-12-31", freq='D')
    return pd.Series(np.random.normal(0.0005, 0.01, len(dates)), index=dates)

@pytest.fixture
def benchmark_data(returns_data):
    return pd.Series(np.random.normal(0.0004, 0.008, len(returns_data)), index=returns_data.index)

class TestSummaryPlots:
    def test_plot_snapshot_layouts(self, returns_data):
        # Test 2x2 layout
        fig2x2 = plot_snapshot(returns_data, layout="2x2", show=False)
        assert isinstance(fig2x2, plt.Figure)
        plt.close(fig2x2)

        # Test 3x2 layout
        fig3x2 = plot_snapshot(returns_data, layout="3x2", show=False)
        assert isinstance(fig3x2, plt.Figure)
        plt.close(fig3x2)

        # Test 2x3 layout
        fig2x3 = plot_snapshot(returns_data, layout="2x3", show=False)
        assert isinstance(fig2x3, plt.Figure)
        plt.close(fig2x3)

    def test_plot_snapshot_with_benchmark(self, returns_data, benchmark_data):
        fig = plot_snapshot(
            returns_data, 
            benchmark_returns=benchmark_data, 
            metrics={"Sharpe": 1.5},
            show=False
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_metrics_table(self):
        fig, ax = plt.subplots()
        metrics = {"Return": 0.15, "Sharpe": 1.2, "Trades": 50}
        _plot_metrics_table(ax, metrics)
        # Check if table was added
        assert len(ax.tables) > 0
        plt.close(fig)

        # Test empty metrics
        fig, ax = plt.subplots()
        _plot_metrics_table(ax, {})
        assert len(ax.texts) > 0 # Should show "No metrics provided"
        plt.close(fig)

    def test_format_metric_value(self):
        assert _format_metric_value(0.12345) == "0.1235"
        assert _format_metric_value(10.5) == "10.50"
        assert _format_metric_value(1000) == "1,000"
        assert _format_metric_value("text") == "text"

    def test_yearly_returns(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_yearly_returns(ax, returns_data, benchmark_returns=benchmark_data)
        assert len(ax.patches) > 0 # Bars
        plt.close(fig)

    def test_daily_returns(self, returns_data):
        fig, ax = plt.subplots()
        _plot_daily_returns(ax, returns_data, plot_type="bar", show_bands=True)
        assert len(ax.patches) > 0 # Bars
        assert len(ax.lines) > 0 # Bands/lines
        plt.close(fig)
        
        # Test scatter
        fig, ax = plt.subplots()
        _plot_daily_returns(ax, returns_data, plot_type="scatter")
        assert len(ax.collections) > 0 # Scatter points
        plt.close(fig)
