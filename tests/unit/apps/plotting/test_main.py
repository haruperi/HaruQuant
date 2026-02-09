import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock
from apps.plotting.main import plot, _determine_layout, _extract_data

@pytest.fixture
def mock_results():
    dates = pd.date_range("2024-01-01", periods=100)
    
    # Mock Strategy with OHLC data
    mock_strategy = MagicMock()
    mock_strategy.data.df = pd.DataFrame({
        "Open": np.random.uniform(100, 110, 100),
        "High": np.random.uniform(100, 115, 100),
        "Low": np.random.uniform(90, 100, 100),
        "Close": np.random.uniform(95, 110, 100),
        "Volume": np.random.uniform(1000, 5000, 100)
    }, index=dates)
    mock_strategy._indicators = []

    # Mock Broker with Equity and Trades
    mock_broker = MagicMock()
    mock_broker.equity = pd.Series(np.linspace(10000, 11000, 100), index=dates)
    
    mock_trade = MagicMock()
    mock_trade.entry_time = dates[10]
    mock_trade.exit_time = dates[20]
    mock_trade.entry_price = 100
    mock_trade.exit_price = 105
    mock_trade.size = 1
    mock_trade.pl = 5
    mock_trade.pl_pct = 0.05
    mock_trade.is_long = True
    mock_broker.closed_trades = [mock_trade]

    return {
        "broker": mock_broker,
        "strategy": mock_strategy,
        "equity": mock_broker.equity.values,
        "trades": [mock_trade],
        "stats": {}
    }

class TestMainPlot:
    def test_plot_validation(self):
        """Test input validation."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            plot("not a dict")
            
        with pytest.raises(ValueError, match="missing required keys"):
            plot({"broker": None}) # Missing strategy

        with pytest.raises(ValueError, match="Unsupported backend"):
            plot({"broker": MagicMock(), "strategy": MagicMock()}, backend="invalid")

    def test_extract_data(self, mock_results):
        """Test data extraction helper."""
        data = _extract_data(mock_results)
        
        assert data["ohlc"] is not None
        assert data["equity"] is not None
        assert data["dates"] is not None
        assert len(data["trades"]) == 1
        assert data["drawdown"] is not None

    def test_determine_layout(self):
        """Test layout determination logic."""
        panels = _determine_layout(
            plot_equity=True,
            plot_returns=True,
            plot_drawdown=True,
            has_ohlc=True
        )
        assert panels == ["ohlc", "equity", "drawdown", "returns"]

        panels = _determine_layout(
            plot_equity=False,
            plot_returns=False,
            plot_drawdown=False,
            has_ohlc=False
        )
        assert panels == ["equity"] # Default fallback

    def test_plot_matplotlib_full(self, mock_results):
        """Test full Matplotlib plot generation."""
        fig = plot(
            mock_results,
            backend="matplotlib",
            plot_equity=True,
            plot_returns=True,
            plot_drawdown=True,
            plot_trades=True
        )
        
        assert isinstance(fig, plt.Figure)
        assert len(fig.axes) > 0
        plt.close(fig)

    def test_plot_matplotlib_simple(self, mock_results):
        """Test simple plot."""
        fig = plot(
            mock_results,
            backend="matplotlib",
            plot_equity=True,
            plot_returns=False,
            plot_drawdown=False,
            plot_trades=False
        )
        
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_bokeh_fallback(self, mock_results):
        """Test Bokeh backend fallback (warns and uses matplotlib)."""
        with pytest.warns(UserWarning, match="Bokeh backend not yet fully implemented"):
            fig = plot(mock_results, backend="bokeh")
            assert isinstance(fig, plt.Figure) # Returns mpl figure due to fallback
            plt.close(fig)
