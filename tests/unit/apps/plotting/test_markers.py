import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.markers import (
    _plot_entry_markers,
    _plot_exit_markers,
    _plot_trade_lines
)

@pytest.fixture
def sample_trades():
    dates = pd.date_range("2024-01-01", periods=10)
    return [
        {
            'entry_time': dates[0],
            'entry_price': 100.0,
            'exit_time': dates[2],
            'exit_price': 105.0,
            'size': 1.0,
            'is_long': True,
            'pl': 5.0,
            'pl_pct': 0.05,
            'tag': 'setup_A'
        },
        {
            'entry_time': dates[3],
            'entry_price': 110.0,
            'exit_time': dates[5],
            'exit_price': 100.0,
            'size': 0.5,
            'is_long': False, # Short
            'pl': 5.0, # Short from 110 to 100 is profit
            'pl_pct': 0.09
        },
        {
            'entry_time': dates[6],
            'entry_price': 100.0,
            'exit_time': dates[8],
            'exit_price': 90.0,
            'size': 1.0,
            'is_long': True,
            'pl': -10.0,
            'pl_pct': -0.1
        }
    ]

class TestEntryMarkers:
    def test_plot_entry_markers_matplotlib(self, sample_trades):
        """Test plotting entry markers with Matplotlib."""
        fig, ax = plt.subplots()
        _plot_entry_markers(ax, sample_trades)
        
        # Verify scatter collections added (long and short are separate)
        assert len(ax.collections) > 0
        plt.close(fig)

    def test_plot_entry_markers_bokeh(self, sample_trades):
        """Test plotting entry markers with Bokeh."""
        with patch("apps.plotting.markers.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            _plot_entry_markers(mock_fig, sample_trades, backend="bokeh")
            
            assert mock_fig.triangle.called # Long entries
            assert mock_fig.inverted_triangle.called # Short entries
            assert mock_fig.add_tools.called # Hover tools

class TestExitMarkers:
    def test_plot_exit_markers_matplotlib(self, sample_trades):
        """Test plotting exit markers with Matplotlib."""
        fig, ax = plt.subplots()
        _plot_exit_markers(ax, sample_trades)
        
        # Verify scatter collections (profit and loss are separate)
        assert len(ax.collections) > 0
        plt.close(fig)

    def test_plot_exit_markers_sized(self, sample_trades):
        """Test plotting sized exit markers."""
        fig, ax = plt.subplots()
        _plot_exit_markers(ax, sample_trades, size_by_pl=True)
        assert len(ax.collections) > 0
        plt.close(fig)

    def test_plot_exit_markers_bokeh(self, sample_trades):
        """Test plotting exit markers with Bokeh."""
        with patch("apps.plotting.markers.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            _plot_exit_markers(mock_fig, sample_trades, backend="bokeh")
            
            assert mock_fig.circle.call_count >= 1

class TestTradeLines:
    def test_plot_trade_lines_matplotlib(self, sample_trades):
        """Test plotting trade lines with Matplotlib."""
        fig, ax = plt.subplots()
        _plot_trade_lines(ax, sample_trades)
        
        # Verify lines added
        assert len(ax.lines) > 0
        plt.close(fig)

    def test_plot_trade_lines_bokeh(self, sample_trades):
        """Test plotting trade lines with Bokeh."""
        with patch("apps.plotting.markers.BOKEH_AVAILABLE", True):
            mock_fig = MagicMock()
            _plot_trade_lines(mock_fig, sample_trades, backend="bokeh")
            
            assert mock_fig.line.call_count >= 1
