import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.charts import (
    _plot_ohlc_matplotlib,
    _plot_line,
    _plot_volume_matplotlib,
    _plot_ohlc_bokeh,
    _plot_volume_bokeh
)

@pytest.fixture
def ohlc_data():
    """Create sample OHLC data."""
    dates = pd.date_range("2024-01-01", periods=10)
    data = pd.DataFrame({
        "Open": np.random.rand(10) * 100,
        "High": np.random.rand(10) * 100 + 10,
        "Low": np.random.rand(10) * 100 - 10,
        "Close": np.random.rand(10) * 100,
        "Volume": np.random.randint(1000, 5000, 10)
    }, index=dates)
    return data

@pytest.fixture
def mock_bokeh():
    """Mock bokeh dependencies."""
    with patch("apps.plotting.charts.BOKEH_AVAILABLE", True):
        with patch("apps.plotting.charts.bokeh_figure") as mock_fig:
            yield mock_fig

class TestOhlcMatplotlib:
    def test_plot_ohlc_matplotlib_basic(self, ohlc_data):
        """Test basic Matplotlib OHLC plotting."""
        fig, ax = plt.subplots()
        ax = _plot_ohlc_matplotlib(ax, ohlc_data)
        
        # Check if lines (wicks) and rectangles (bodies) are added
        assert len(ax.lines) > 0
        assert len(ax.patches) > 0
        
        plt.close(fig)

    def test_plot_ohlc_matplotlib_missing_cols(self):
        """Test error handling for missing columns."""
        fig, ax = plt.subplots()
        data = pd.DataFrame({"Open": [1]})
        
        with pytest.raises(ValueError, match="Missing required columns"):
            _plot_ohlc_matplotlib(ax, data)
        
        plt.close(fig)

class TestLinePlot:
    def test_plot_line_matplotlib(self):
        """Test basic Matplotlib line plotting."""
        fig, ax = plt.subplots()
        data = pd.Series([1, 2, 3], index=pd.date_range("2024-01-01", periods=3))
        
        ax = _plot_line(ax, data, label="Test")
        
        assert len(ax.get_lines()) == 1
        assert ax.get_lines()[0].get_label() == "Test"
        
        plt.close(fig)

    def test_plot_line_bokeh(self, mock_bokeh):
        """Test basic Bokeh line plotting."""
        mock_fig = MagicMock()
        data = pd.Series([1, 2, 3], index=pd.date_range("2024-01-01", periods=3))
        
        _plot_line(mock_fig, data, backend="bokeh", label="Test")
        
        mock_fig.line.assert_called_once()

class TestVolumeMatplotlib:
    def test_plot_volume_matplotlib_basic(self, ohlc_data):
        """Test basic Matplotlib volume plotting."""
        fig, ax = plt.subplots()
        ax = _plot_volume_matplotlib(ax, ohlc_data)
        
        # Check if bars are added (containers or patches)
        assert len(ax.containers) > 0 or len(ax.patches) > 0
        
        plt.close(fig)

    def test_plot_volume_matplotlib_missing_col(self):
        """Test error handling for missing volume column."""
        fig, ax = plt.subplots()
        data = pd.DataFrame({"Open": [1]})
        
        with pytest.raises(ValueError, match="Volume column is required"):
            _plot_volume_matplotlib(ax, data)
        
        plt.close(fig)

class TestBokehCharts:
    def test_plot_ohlc_bokeh(self, ohlc_data, mock_bokeh):
        """Test Bokeh OHLC plotting."""
        _plot_ohlc_bokeh(ohlc_data)
        mock_bokeh.return_value.segment.assert_called()
        mock_bokeh.return_value.vbar.assert_called()

    def test_plot_volume_bokeh(self, ohlc_data, mock_bokeh):
        """Test Bokeh volume plotting."""
        _plot_volume_bokeh(ohlc_data)
        mock_bokeh.return_value.vbar.assert_called()
