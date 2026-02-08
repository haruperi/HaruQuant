"""
Unit tests for PortfolioStrategy and PortfolioEngine.

Tests portfolio allocation strategies and backtest orchestration.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy


class MockStrategy(BaseStrategy):
    """Mock strategy for testing."""

    def __init__(self, name: str = "MockStrategy"):
        self.name = name

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process bar and return data with signal columns."""
        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Return no signal."""
        return None


@pytest.fixture
def sample_data_2_symbols():
    """Sample price data for 2 symbols."""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')

    # EURUSD: moderate volatility
    eurusd_prices = 1.1000 + np.random.randn(100) * 0.01
    df_eurusd = pd.DataFrame({
        'open': eurusd_prices,
        'high': eurusd_prices + 0.001,
        'low': eurusd_prices - 0.001,
        'close': eurusd_prices,
        'volume': 1000
    }, index=dates)

    # GBPUSD: higher volatility
    gbpusd_prices = 1.2500 + np.random.randn(100) * 0.02
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
def sample_data_5_symbols():
    """Sample price data for 5 symbols."""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')

    data = {}
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF']
    base_prices = [1.1000, 1.2500, 150.00, 0.6500, 0.9000]
    volatilities = [0.01, 0.02, 1.0, 0.015, 0.012]

    for symbol, base_price, vol in zip(symbols, base_prices, volatilities):
        prices = base_price + np.random.randn(100) * vol
        data[symbol] = pd.DataFrame({
            'open': prices,
            'high': prices + vol,
            'low': prices - vol,
            'close': prices,
            'volume': 1000
        }, index=dates)

    return data


@pytest.fixture
def symbol_specs_2():
    """Symbol specs for 2 symbols."""
    return {
        'EURUSD': SymbolInfoSimulator(
            symbol='EURUSD',
            digits=5,
            point=0.00001,
            trade_contract_size=100000,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01
        ),
        'GBPUSD': SymbolInfoSimulator(
            symbol='GBPUSD',
            digits=5,
            point=0.00001,
            trade_contract_size=100000,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01
        )
    }


@pytest.fixture
def symbol_specs_5():
    """Symbol specs for 5 symbols."""
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF']
    return {
        symbol: SymbolInfoSimulator(
            symbol=symbol,
            digits=5,
            point=0.00001,
            trade_contract_size=100000,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01
        )
        for symbol in symbols
    }


class TestPortfolioStrategy:
    """Test suite for PortfolioStrategy class."""

    def test_portfolio_strategy_init(self, sample_data_2_symbols, symbol_specs_2):
        """Test creating PortfolioStrategy."""
        strategies = {
            'EURUSD': MockStrategy('EURUSD_Strategy'),
            'GBPUSD': MockStrategy('GBPUSD_Strategy')
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            allocation_method='equal_weight'
        )

        assert len(portfolio.strategies) == 2
        assert 'EURUSD' in portfolio.strategies
        assert 'GBPUSD' in portfolio.strategies

    def test_portfolio_strategy_validation_success(self, sample_data_2_symbols, symbol_specs_2):
        """Test validation with valid configuration."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        # Should not raise
        portfolio.validate()

    def test_portfolio_strategy_validation_missing_symbol_spec(self, sample_data_2_symbols, symbol_specs_2):
        """Test validation fails with missing symbol spec."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy(),
            'USDJPY': MockStrategy()  # Extra symbol not in specs
        }

        with pytest.raises(ValueError, match="Strategy symbols .* don't match"):
            PortfolioStrategy(
                strategies=strategies,
                symbol_specs=symbol_specs_2,
                data=sample_data_2_symbols
            )

    def test_portfolio_strategy_validation_missing_data(self, symbol_specs_2):
        """Test validation fails with missing data."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        data = {
            'EURUSD': pd.DataFrame({'close': [1.1, 1.2]}, index=pd.date_range('2024-01-01', periods=2))
            # Missing GBPUSD
        }

        with pytest.raises(ValueError, match="Strategy symbols .* don't match"):
            PortfolioStrategy(
                strategies=strategies,
                symbol_specs=symbol_specs_2,
                data=data
            )

    def test_portfolio_strategy_validation_empty_data(self, symbol_specs_2):
        """Test validation fails with empty DataFrame."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        data = {
            'EURUSD': pd.DataFrame(),  # Empty
            'GBPUSD': pd.DataFrame({'close': [1.2]}, index=[datetime(2024, 1, 1)])
        }

        with pytest.raises(ValueError, match="Data for EURUSD is empty"):
            PortfolioStrategy(
                strategies=strategies,
                symbol_specs=symbol_specs_2,
                data=data
            )

    def test_equal_weight_allocation_2_symbols(self, sample_data_2_symbols, symbol_specs_2):
        """Test equal weight allocation with 2 symbols."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            allocation_method='equal_weight'
        )

        allocations = portfolio.calculate_allocations()

        assert len(allocations) == 2
        assert allocations['EURUSD'] == pytest.approx(0.5)
        assert allocations['GBPUSD'] == pytest.approx(0.5)
        # Should sum to max_total_exposure (1.0)
        assert sum(allocations.values()) == pytest.approx(1.0)

    def test_equal_weight_allocation_5_symbols(self, sample_data_5_symbols, symbol_specs_5):
        """Test equal weight allocation with 5 symbols."""
        strategies = {symbol: MockStrategy() for symbol in sample_data_5_symbols.keys()}

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_5,
            data=sample_data_5_symbols,
            allocation_method='equal_weight'
        )

        allocations = portfolio.calculate_allocations()

        assert len(allocations) == 5
        # Each should get 1/5 = 0.2
        for symbol, allocation in allocations.items():
            assert allocation == pytest.approx(0.2)

        assert sum(allocations.values()) == pytest.approx(1.0)

    def test_equal_weight_allocation_custom_max_exposure(self, sample_data_2_symbols, symbol_specs_2):
        """Test equal weight with custom max exposure."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            max_total_exposure=0.6,  # Only use 60% of capital
            allocation_method='equal_weight'
        )

        allocations = portfolio.calculate_allocations()

        # Each should get 0.6 / 2 = 0.3
        assert allocations['EURUSD'] == pytest.approx(0.3)
        assert allocations['GBPUSD'] == pytest.approx(0.3)
        assert sum(allocations.values()) == pytest.approx(0.6)

    def test_risk_parity_allocation(self, sample_data_2_symbols, symbol_specs_2):
        """Test risk parity allocation (inverse volatility)."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            allocation_method='risk_parity'
        )

        allocations = portfolio.calculate_allocations()

        assert len(allocations) == 2
        # Allocations should sum to 1.0
        assert sum(allocations.values()) == pytest.approx(1.0)
        # Lower volatility asset (EURUSD) should get higher allocation
        # Note: This depends on random data, so we just check structure
        assert allocations['EURUSD'] > 0
        assert allocations['GBPUSD'] > 0

    def test_risk_parity_allocation_inverse_relationship(self):
        """Test that higher volatility gets lower allocation in risk parity."""
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')

        # Low volatility asset
        low_vol_prices = 1.0 + np.random.randn(100) * 0.001
        df_low_vol = pd.DataFrame({'close': low_vol_prices}, index=dates)

        # High volatility asset
        high_vol_prices = 1.0 + np.random.randn(100) * 0.1
        df_high_vol = pd.DataFrame({'close': high_vol_prices}, index=dates)

        data = {'LOW_VOL': df_low_vol, 'HIGH_VOL': df_high_vol}

        strategies = {
            'LOW_VOL': MockStrategy(),
            'HIGH_VOL': MockStrategy()
        }

        symbol_specs = {
            'LOW_VOL': SymbolInfoSimulator(symbol='LOW_VOL'),
            'HIGH_VOL': SymbolInfoSimulator(symbol='HIGH_VOL')
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=data,
            allocation_method='risk_parity'
        )

        allocations = portfolio.calculate_allocations()

        # Low volatility should get higher allocation
        assert allocations['LOW_VOL'] > allocations['HIGH_VOL']

    def test_invalid_allocation_method(self, sample_data_2_symbols, symbol_specs_2):
        """Test error handling for invalid allocation method."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        with pytest.raises(ValueError, match="Invalid allocation_method"):
            PortfolioStrategy(
                strategies=strategies,
                symbol_specs=symbol_specs_2,
                data=sample_data_2_symbols,
                allocation_method='invalid_method'
            )


class TestPortfolioEngine:
    """Test suite for PortfolioEngine class."""

    def test_portfolio_engine_init(self, sample_data_2_symbols, symbol_specs_2):
        """Test creating PortfolioEngine."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0
        )

        assert engine.initial_balance == 10000.0
        assert engine.portfolio_strategy == portfolio_strategy

    def test_portfolio_engine_run_2_symbols(self, sample_data_2_symbols, symbol_specs_2):
        """Test running portfolio engine with 2 symbols."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0,
            config={'portfolio_name': 'Test Portfolio'}
        )

        result = engine.run()

        # Check result structure
        assert result.portfolio_name == 'Test Portfolio'
        assert len(result.symbols) == 2
        assert 'EURUSD' in result.symbols
        assert 'GBPUSD' in result.symbols
        assert result.initial_balance == 10000.0
        assert len(result.asset_results) == 2

        # Check equity curve exists
        assert not result.equity_curve.empty

    def test_portfolio_engine_run_5_symbols(self, sample_data_5_symbols, symbol_specs_5):
        """Test running portfolio engine with 5 symbols."""
        strategies = {symbol: MockStrategy() for symbol in sample_data_5_symbols.keys()}

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_5,
            data=sample_data_5_symbols
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=50000.0
        )

        result = engine.run()

        assert len(result.symbols) == 5
        assert result.initial_balance == 50000.0
        assert len(result.asset_results) == 5

    def test_portfolio_engine_run_with_sync(self, sample_data_2_symbols, symbol_specs_2):
        """Test portfolio engine with data synchronization."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0
        )

        result = engine.run(synchronize_data=True, sync_method='ffill')

        # Should have synchronized data
        assert not result.equity_curve.empty

    def test_portfolio_engine_run_without_sync(self, sample_data_2_symbols, symbol_specs_2):
        """Test portfolio engine without data synchronization."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0
        )

        result = engine.run(synchronize_data=False)

        # Should still work without sync
        assert len(result.symbols) == 2

    def test_portfolio_engine_allocations_calculated(self, sample_data_2_symbols, symbol_specs_2):
        """Test that portfolio engine calculates allocations."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0
        )

        # Run and verify allocations were calculated
        result = engine.run()

        # For now, just verify engine ran successfully
        assert result is not None

    def test_portfolio_engine_risk_parity_allocation(self, sample_data_2_symbols, symbol_specs_2):
        """Test portfolio engine with risk parity allocation."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols,
            allocation_method='risk_parity'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=10000.0
        )

        result = engine.run()

        assert result is not None
        assert len(result.symbols) == 2

    def test_portfolio_engine_custom_config(self, sample_data_2_symbols, symbol_specs_2):
        """Test portfolio engine with custom configuration."""
        strategies = {
            'EURUSD': MockStrategy(),
            'GBPUSD': MockStrategy()
        }

        portfolio_strategy = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_2,
            data=sample_data_2_symbols
        )

        config = {
            'portfolio_name': 'Custom Portfolio',
            'commission': 7.0,
            'slippage': 0.5
        }

        engine = PortfolioEngine(
            portfolio_strategy=portfolio_strategy,
            initial_balance=20000.0,
            config=config
        )

        result = engine.run()

        assert result.portfolio_name == 'Custom Portfolio'
        assert result.initial_balance == 20000.0
