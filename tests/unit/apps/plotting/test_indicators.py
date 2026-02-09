import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.indicators import (
    _classify_indicator,
    _plot_overlay_indicators,
    _plot_panel_indicators,
    _create_indicator_subplot
)

@pytest.fixture
def price_data():
    """Create sample price data."""
    dates = pd.date_range("2024-01-01", periods=100)
    return pd.Series(np.linspace(100, 110, 100), index=dates)

@pytest.fixture
def indicators_data(price_data):
    """Create sample indicator data."""
    return {
        'SMA_20': price_data.rolling(20).mean(),
        'RSI': pd.Series(np.random.uniform(30, 70, 100), index=price_data.index)
    }

class TestIndicatorClassification:
    def test_classify_indicator_overlay(self):
        """Test classification of overlay indicators."""
        plot_type, hints = _classify_indicator("sma_20")
        assert plot_type == "overlay"
        assert hints["linestyle"] == "-"

        plot_type, hints = _classify_indicator("Bollinger Bands")
        assert plot_type == "overlay"

    def test_classify_indicator_panel(self):
        """Test classification of panel indicators."""
        plot_type, hints = _classify_indicator("RSI")
        assert plot_type == "panel"
        assert "levels" in hints
        assert hints["levels"] == [30, 70]

        plot_type, hints = _classify_indicator("MACD")
        assert plot_type == "panel"

    def test_classify_indicator_metadata(self):
        """Test classification with metadata override."""
        metadata = {"plot_type": "panel", "style": {"color": "red"}}
        plot_type, hints = _classify_indicator("Custom", metadata)
        assert plot_type == "panel"
        assert hints["color"] == "red"

class TestOverlayIndicators:
    def test_plot_overlay_indicators_basic(self, price_data, indicators_data):
        """Test plotting overlay indicators."""
        fig, ax = plt.subplots()
        ax.plot(price_data.index, price_data.values)
        
        _plot_overlay_indicators(ax, {'SMA_20': indicators_data['SMA_20']})
        
        # Verify lines added
        assert len(ax.lines) > 1 # Price + SMA
        plt.close(fig)

    def test_plot_overlay_indicators_dataframe(self, price_data):
        """Test plotting overlay indicators from DataFrame (e.g. BBands)."""
        bbands = pd.DataFrame({
            'upper': price_data + 2,
            'lower': price_data - 2
        }, index=price_data.index)
        
        fig, ax = plt.subplots()
        _plot_overlay_indicators(ax, {'BBands': bbands})
        
        # Verify lines and fill
        assert len(ax.lines) > 0
        assert len(ax.collections) > 0 # Fill between
        plt.close(fig)

class TestPanelIndicators:
    def test_plot_panel_indicators(self, indicators_data, price_data):
        """Test plotting panel indicators."""
        fig, axes = _plot_panel_indicators(
            {'RSI': indicators_data['RSI']},
            dates=price_data.index
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(axes) == 1
        assert len(axes[0].lines) > 0
        plt.close(fig)

    def test_plot_panel_indicators_multiple(self, indicators_data, price_data):
        """Test plotting multiple panel indicators."""
        fig, axes = _plot_panel_indicators(
            {'RSI': indicators_data['RSI'], 'MACD': indicators_data['RSI']}, # Reusing RSI as dummy
            dates=price_data.index
        )
        
        assert len(axes) == 2
        plt.close(fig)

    def test_create_indicator_subplot(self, price_data, indicators_data):
        """Test creating an indicator subplot."""
        fig, ax = plt.subplots()
        ax.plot(price_data.index, price_data.values)
        
        indicator_ax = _create_indicator_subplot(
            ax,
            'RSI',
            indicators_data['RSI']
        )
        
        assert isinstance(indicator_ax, plt.Axes)
        assert indicator_ax != ax
        plt.close(fig)
