import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from apps.plotting.distribution import (
    _calculate_optimal_bins,
    _plot_histogram,
    _plot_qq,
    _plot_distribution
)

@pytest.fixture
def returns_data():
    """Create sample returns data."""
    # Create normal distribution data
    np.random.seed(42)
    return pd.Series(np.random.normal(0.01, 0.02, 100))

class TestOptimalBins:
    def test_calculate_optimal_bins_auto(self, returns_data):
        """Test automatic bin calculation."""
        bins = _calculate_optimal_bins(returns_data, method="auto")
        assert isinstance(bins, int)
        assert 10 <= bins <= 100

    def test_calculate_optimal_bins_methods(self, returns_data):
        """Test different bin calculation methods."""
        methods = ["fd", "sturges", "scott", "sqrt"]
        for method in methods:
            bins = _calculate_optimal_bins(returns_data, method=method)
            assert isinstance(bins, int)
            assert bins > 0

class TestHistogramPlot:
    def test_plot_histogram_matplotlib(self, returns_data):
        """Test Matplotlib histogram plot."""
        fig, ax = plt.subplots()
        _plot_histogram(ax, returns_data)
        
        # Verify histogram patches/containers created
        assert len(ax.patches) > 0 or len(ax.containers) > 0
        
        plt.close(fig)

    def test_plot_histogram_options(self, returns_data):
        """Test histogram options."""
        fig, ax = plt.subplots()
        _plot_histogram(
            ax, 
            returns_data,
            show_normal=False,
            show_mean=False,
            show_median=False,
            show_std=False,
            show_stats=False
        )
        plt.close(fig)

    def test_plot_histogram_empty_error(self):
        """Test error for empty returns."""
        fig, ax = plt.subplots()
        with pytest.raises(ValueError, match="Returns series is empty"):
            _plot_histogram(ax, pd.Series([], dtype=float))
        plt.close(fig)

class TestQQPlot:
    def test_plot_qq_basic(self, returns_data):
        """Test Q-Q plot."""
        fig, ax = plt.subplots()
        _plot_qq(ax, returns_data)
        
        # Verify scatter plot added
        assert len(ax.collections) > 0
        
        plt.close(fig)

    def test_plot_qq_outliers(self, returns_data):
        """Test Q-Q plot with outliers."""
        # Add extreme outliers
        data = pd.concat([returns_data, pd.Series([1.0, -1.0])])
        
        fig, ax = plt.subplots()
        _plot_qq(ax, data, highlight_outliers=True)
        plt.close(fig)

class TestDistributionPlot:
    def test_plot_distribution_full(self, returns_data):
        """Test full distribution plot."""
        fig, ax = plt.subplots()
        _plot_distribution(
            ax,
            returns_data,
            show_histogram=True,
            show_kde=True,
            show_normal=True,
            show_percentiles=True,
            show_var=True
        )
        
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_plot_distribution_minimal(self, returns_data):
        """Test minimal distribution plot."""
        fig, ax = plt.subplots()
        _plot_distribution(
            ax,
            returns_data,
            show_histogram=False,
            show_kde=False,
            show_normal=False,
            show_percentiles=False,
            show_var=False,
            show_stats=False
        )
        plt.close(fig)
