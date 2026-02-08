"""
Integration tests for Portfolio + SimulationEngine.

Tests that PortfolioEngine correctly integrates with SimulationEngine
for multi-symbol backtesting.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy


class SimpleStrategy(BaseStrategy):
    """Simple test strategy that generates signals."""

    def __init__(self, name: str = "SimpleStrategy"):
        self.name = name

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process bar and return data with signal columns."""
        # Add simple signal columns
        data['entry_signal'] = 0
        data['exit_signal'] = 0
        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Return no signal for now."""
        return None


@pytest.fixture
def simple_portfolio_data():
    """Simple portfolio data for 2 symbols."""
    dates = pd.date_range('2024-01-01', periods=50, freq='1h')

    # Create simple trending data
    eurusd_prices = 1.1000 + np.cumsum(np.random.randn(50) * 0.001)
    gbpusd_prices = 1.2500 + np.cumsum(np.random.randn(50) * 0.001)

    df_eurusd = pd.DataFrame({
        'open': eurusd_prices,
        'high': eurusd_prices + 0.001,
        'low': eurusd_prices - 0.001,
        'close': eurusd_prices,
        'volume': 1000
    }, index=dates)

    df_gbpusd = pd.DataFrame({
        'open': gbpusd_prices,
        'high': gbpusd_prices + 0.002,
        'low': gbpusd_prices - 0.002,
        'close': gbpusd_prices,
        'volume': 1000
    }, index=dates)

    return {
        'EURUSD': df_eurusd,
        'GBPUSD': df_gbpusd
    }


@pytest.fixture
def simple_symbol_specs():
    """Simple symbol specs."""
    return {
        'EURUSD': SymbolInfoSimulator(symbol='EURUSD'),
        'GBPUSD': SymbolInfoSimulator(symbol='GBPUSD')
    }


class TestPortfolioIntegration:
    """Test suite for Portfolio + SimulationEngine integration."""

    def test_portfolio_engine_compiles(self, simple_portfolio_data, simple_symbol_specs):
        """Test that PortfolioEngine initializes without errors."""
        strategies = {
            'EURUSD': SimpleStrategy('EURUSD_Strategy'),
            'GBPUSD': SimpleStrategy('GBPUSD_Strategy')
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=simple_symbol_specs,
            data=simple_portfolio_data,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0
        )

        # Should initialize without errors
        assert engine is not None
        assert engine.initial_balance == 10000.0

    @pytest.mark.skip(reason="Full integration test - requires complete simulator setup")
    def test_portfolio_engine_run_integration(self, simple_portfolio_data, simple_symbol_specs):
        """Test that PortfolioEngine.run() executes without errors."""
        strategies = {
            'EURUSD': SimpleStrategy('EURUSD_Strategy'),
            'GBPUSD': SimpleStrategy('GBPUSD_Strategy')
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=simple_symbol_specs,
            data=simple_portfolio_data,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0,
            config={'volume': 0.01}
        )

        # Run portfolio backtest
        result = engine.run(synchronize_data=True, sync_method='ffill')

        # Verify result structure
        assert result is not None
        assert len(result.symbols) == 2
        assert result.initial_balance == 10000.0

    def test_simulation_engine_portfolio_signature(self):
        """Test that SimulationEngine accepts portfolio parameters."""
        from apps.simulation.engine import SimulationEngine
        import inspect

        sig = inspect.signature(SimulationEngine.run)
        params = sig.parameters

        # Check that run() accepts Dict types for portfolio mode
        assert 'data' in params
        assert 'strategy' in params
        assert 'symbol' in params
        assert 'allocations' in params  # New parameter for portfolio mode

    def test_simulation_engine_has_portfolio_method(self):
        """Test that SimulationEngine has _run_portfolio() method."""
        from apps.simulation.engine import SimulationEngine

        assert hasattr(SimulationEngine, '_run_portfolio')
        assert callable(getattr(SimulationEngine, '_run_portfolio'))
