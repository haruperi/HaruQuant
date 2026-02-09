import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.rolling import (
    _plot_rolling_volatility,
    _plot_rolling_sharpe,
    _plot_rolling_sortino,
    _plot_rolling_beta,
    _plot_rolling_returns
)

@pytest.fixture
def returns_data():
    dates = pd.date_range("2024-01-01", periods=100)
    return pd.Series(np.random.normal(0.001, 0.01, 100), index=dates)

@pytest.fixture
def benchmark_data(returns_data):
    return pd.Series(np.random.normal(0.0008, 0.008, 100), index=returns_data.index)

class TestRollingMetrics:
    def test_rolling_volatility(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_rolling_volatility(ax, returns_data, benchmark_returns=benchmark_data, window=10)
        assert len(ax.lines) >= 2 # Strategy + Benchmark
        plt.close(fig)

    def test_rolling_sharpe(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_rolling_sharpe(ax, returns_data, benchmark_returns=benchmark_data, window=20)
        assert len(ax.lines) >= 2
        plt.close(fig)

    def test_rolling_sortino(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_rolling_sortino(ax, returns_data, benchmark_returns=benchmark_data, window=20)
        assert len(ax.lines) >= 2
        plt.close(fig)

    def test_rolling_beta(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_rolling_beta(ax, returns_data, benchmark_data, window=30)
        
        # Check for main line and reference line (beta=1)
        assert len(ax.lines) >= 2
        # Check for main line and reference line (beta=1)
        assert len(ax.lines) >= 2
        # Shaded regions might not be created if beta doesn't cross 1.0 with random data
        # so we just check the lines are there
        plt.close(fig)

    def test_rolling_returns(self, returns_data, benchmark_data):
        fig, ax = plt.subplots()
        _plot_rolling_returns(ax, returns_data, benchmark_returns=benchmark_data, window=10, annualize=True)
        assert len(ax.lines) >= 2
        plt.close(fig)
