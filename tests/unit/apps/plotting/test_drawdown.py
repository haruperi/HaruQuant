import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.drawdown import (
    _calculate_drawdown,
    _identify_drawdown_periods,
    _plot_drawdown,
    _plot_drawdown_periods
)

@pytest.fixture
def equity_curve():
    """Create sample equity curve."""
    dates = pd.date_range("2024-01-01", periods=100)
    # create a curve with a drawdown
    values = np.linspace(100, 110, 100)
    values[20:30] = np.linspace(102, 90, 10) # Drawdown
    values[30:50] = np.linspace(90, 105, 20) # Recovery
    return pd.Series(values, index=dates)

class TestDrawdownCalculation:
    def test_calculate_drawdown(self, equity_curve):
        """Test drawdown calculation."""
        dd = _calculate_drawdown(equity_curve)
        assert len(dd) == len(equity_curve)
        assert dd.max() <= 0
        assert dd.min() < 0

    def test_identify_drawdown_periods(self, equity_curve):
        """Test identifying drawdown periods."""
        dd = _calculate_drawdown(equity_curve)
        periods = _identify_drawdown_periods(dd)
        
        assert len(periods) > 0
        assert "start" in periods[0]
        assert "end" in periods[0]
        assert "duration" in periods[0]
        assert "magnitude" in periods[0]

class TestDrawdownPlots:
    def test_plot_drawdown_matplotlib(self, equity_curve):
        """Test Matplotlib drawdown plot."""
        fig, ax = plt.subplots()
        _plot_drawdown(ax, equity=equity_curve)
        
        # Verify plot elements
        assert len(ax.lines) > 0 or len(ax.collections) > 0
        
        plt.close(fig)

    def test_plot_drawdown_periods(self, equity_curve):
        """Test plotting top drawdown periods."""
        fig, ax = plt.subplots()
        _plot_drawdown_periods(ax, equity=equity_curve, top_n=5)
        
        # Verify bars created
        assert len(ax.patches) > 0 or len(ax.containers) > 0
        
        plt.close(fig)

    def test_drawdown_missing_args(self):
        """Test error for missing arguments."""
        fig, ax = plt.subplots()
        with pytest.raises(ValueError, match="Either drawdown or equity"):
            _plot_drawdown(ax)
        plt.close(fig)
