import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.heatmap import (
    _plot_monthly_heatmap,
    plot_heatmaps,
    _plot_correlation_heatmap
)

@pytest.fixture
def monthly_returns():
    """Create sample daily returns for a year."""
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.01, len(dates)), index=dates)
    return returns

@pytest.fixture
def optimization_results():
    """Create sample optimization results."""
    return pd.DataFrame({
        'param1': [1, 2, 3, 1, 2, 3],
        'param2': [10, 10, 10, 20, 20, 20],
        'sharpe_ratio': [0.5, 1.2, 0.8, 1.5, 2.0, 1.3]
    })

class TestMonthlyHeatmap:
    def test_plot_monthly_heatmap_basic(self, monthly_returns):
        """Test basic monthly heatmap."""
        fig, ax = plt.subplots()
        _plot_monthly_heatmap(ax, monthly_returns)
        
        # Verify heatmap created (collections)
        assert len(ax.collections) > 0
        plt.close(fig)

    def test_plot_monthly_heatmap_options(self, monthly_returns):
        """Test monthly heatmap options."""
        fig, ax = plt.subplots()
        _plot_monthly_heatmap(
            ax, 
            monthly_returns,
            show_ytd=False,
            color_mode="grayscale"
        )
        plt.close(fig)

    def test_plot_monthly_heatmap_invalid_index(self):
        """Test error for invalid index."""
        returns = pd.Series([1, 2, 3]) # No datetime index
        fig, ax = plt.subplots()
        with pytest.raises(ValueError, match="Returns index must be DatetimeIndex"):
            _plot_monthly_heatmap(ax, returns)
        plt.close(fig)

class TestOptimizationHeatmaps:
    def test_plot_heatmaps_matplotlib(self, optimization_results):
        """Test optimization heatmaps with Matplotlib."""
        fig = plot_heatmaps(
            optimization_results,
            metric_column='sharpe_ratio',
            backend='matplotlib'
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_heatmaps_matplotlib_marginals(self, optimization_results):
        """Test optimization heatmaps with marginals."""
        fig = plot_heatmaps(
            optimization_results,
            metric_column='sharpe_ratio',
            show_marginals=True
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_heatmaps_bokeh(self, optimization_results):
        """Test optimization heatmaps with Bokeh."""
        with patch("apps.plotting.heatmap.BOKEH_AVAILABLE", True):
            with patch("bokeh.plotting.figure") as mock_fig:
                with patch("bokeh.layouts.gridplot") as mock_grid:
                    plot_heatmaps(
                        optimization_results,
                        metric_column='sharpe_ratio',
                        backend='bokeh'
                    )
                    mock_grid.assert_called()

class TestCorrelationHeatmap:
    def test_plot_correlation_heatmap(self):
        """Test correlation heatmap."""
        returns_df = pd.DataFrame({
            'Strategy A': [0.01, -0.02, 0.03],
            'Strategy B': [0.02, -0.01, 0.02],
            'Strategy C': [-0.01, 0.01, 0.04]
        })
        fig, ax = plt.subplots()
        _plot_correlation_heatmap(ax, returns_df)
        
        assert len(ax.collections) > 0
        plt.close(fig)
