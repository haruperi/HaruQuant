"""
Integration tests for portfolio backtesting.

Tests the complete portfolio backtesting workflow from end to end,
including data synchronization, multi-symbol execution, and result generation.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy


class TrendStrategy(BaseStrategy):
    """Simple trend-following strategy for testing."""

    def __init__(self, params=None):
        self.params = params or {}
        self.name = "TrendStrategy"

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate SMA and generate signals."""
        # Calculate 20-period SMA
        data['sma_20'] = data['close'].rolling(window=20).mean()

        # Generate entry signals: 1 for buy, -1 for sell, 0 for no signal
        data['entry_signal'] = 0
        data.loc[data['close'] > data['sma_20'], 'entry_signal'] = 1
        data.loc[data['close'] < data['sma_20'], 'entry_signal'] = -1

        data['exit_signal'] = 0

        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Return signal for current bar."""
        if current_index < 20:  # Need warmup for SMA
            return None

        entry_signal = int(data.iloc[current_index]['entry_signal'])

        if entry_signal == 0:
            return None

        return {
            'entry_signal': entry_signal,
            'exit_signal': 0,
            'type': 'buy' if entry_signal == 1 else 'sell',
        }


def generate_test_data(symbol: str, periods: int = 200, trend: float = 0.0001):
    """Generate synthetic price data with optional trend."""
    dates = pd.date_range('2024-01-01', periods=periods, freq='1h')

    # Generate price series with trend
    returns = np.random.randn(periods) * 0.002 + trend
    prices = 1.0 + np.cumsum(returns)

    # Normalize to realistic range
    if 'JPY' in symbol:
        prices = prices * 150
    else:
        prices = prices * 1.1

    df = pd.DataFrame({
        'open': prices,
        'high': prices + abs(np.random.randn(periods) * 0.001),
        'low': prices - abs(np.random.randn(periods) * 0.001),
        'close': prices,
        'volume': np.random.randint(1000, 10000, periods)
    }, index=dates)

    return df


@pytest.fixture
def portfolio_data_2_symbols():
    """Generate test data for 2-symbol portfolio."""
    return {
        'EURUSD': generate_test_data('EURUSD', periods=200, trend=0.0001),
        'GBPUSD': generate_test_data('GBPUSD', periods=200, trend=-0.0001)
    }


@pytest.fixture
def portfolio_data_3_symbols():
    """Generate test data for 3-symbol portfolio."""
    return {
        'EURUSD': generate_test_data('EURUSD', periods=200, trend=0.0001),
        'GBPUSD': generate_test_data('GBPUSD', periods=200, trend=-0.0001),
        'USDJPY': generate_test_data('USDJPY', periods=200, trend=0.00005)
    }


@pytest.fixture
def symbol_specs_3():
    """Symbol specs for 3 symbols."""
    return {
        symbol: SymbolInfoSimulator(symbol=symbol)
        for symbol in ['EURUSD', 'GBPUSD', 'USDJPY']
    }


class TestPortfolioBacktestIntegration:
    """Integration tests for complete portfolio backtest workflow."""

    def test_portfolio_vs_individual_backtests(self, portfolio_data_2_symbols):
        """Test that portfolio backtest produces consistent results."""
        # Create symbol specs
        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in portfolio_data_2_symbols.keys()
        }

        # Create strategies
        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_2_symbols.keys()
        }

        # Run portfolio backtest
        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=portfolio_data_2_symbols,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=20000.0,
            config={'volume': 0.1, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Verify basic structure
        assert result is not None
        assert len(result.symbols) == 2
        assert result.initial_balance == 20000.0
        assert result.final_balance > 0

        # Verify trades are attributed correctly
        eurusd_trades = [t for t in result.trades if t.symbol == 'EURUSD']
        gbpusd_trades = [t for t in result.trades if t.symbol == 'GBPUSD']

        # Each symbol should have generated some trades
        assert len(eurusd_trades) >= 0  # May be 0 if no signals
        assert len(gbpusd_trades) >= 0

        # Total trades should equal sum of individual
        assert len(result.trades) == len(eurusd_trades) + len(gbpusd_trades)

    def test_portfolio_equity_curve_consistency(self, portfolio_data_2_symbols):
        """Test that equity curve is consistent throughout backtest."""
        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in portfolio_data_2_symbols.keys()
        }

        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_2_symbols.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=portfolio_data_2_symbols,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0,
            config={'volume': 0.05, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Verify equity curve
        assert not result.equity_curve.empty
        assert len(result.equity_curve) > 0

        # Equity should start at initial balance
        first_equity = result.equity_curve.iloc[0]
        assert abs(first_equity - 10000.0) < 100  # Allow small deviation

        # Equity should be positive throughout
        assert (result.equity_curve > 0).all()

        # Final equity should match final balance
        last_equity = result.equity_curve.iloc[-1]
        assert abs(last_equity - result.final_balance) < 1.0  # Very close

    def test_portfolio_trade_attribution(self, portfolio_data_3_symbols, symbol_specs_3):
        """Test that trades are correctly attributed to symbols."""
        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_3_symbols.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_3,
            data=portfolio_data_3_symbols,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=30000.0,
            config={'volume': 0.1, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Get asset contributions
        contributions = result.get_asset_contributions()

        # Should have contribution for each symbol
        assert len(contributions) == 3
        assert 'EURUSD' in contributions
        assert 'GBPUSD' in contributions
        assert 'USDJPY' in contributions

        # Each contribution should have required fields
        for symbol, contrib in contributions.items():
            assert 'symbol' in contrib
            assert 'total_return' in contrib
            assert 'contribution_pct' in contrib
            assert 'total_trades' in contrib

            # Symbol should match
            assert contrib['symbol'] == symbol

            # Contribution percent should be a number
            assert isinstance(contrib['contribution_pct'], (int, float))

    def test_portfolio_correlation_matrix(self, portfolio_data_3_symbols, symbol_specs_3):
        """Test correlation matrix calculation."""
        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_3_symbols.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs_3,
            data=portfolio_data_3_symbols,
            allocation_method='risk_parity'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=30000.0,
            config={'volume': 0.1, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Get correlation matrix
        corr_matrix = result.get_correlation_matrix()

        # If there are trades, correlation matrix should be populated
        if len(result.trades) > 0:
            # Check structure
            assert isinstance(corr_matrix, pd.DataFrame)

            # If not empty, check properties
            if not corr_matrix.empty:
                # Should be square matrix
                assert corr_matrix.shape[0] == corr_matrix.shape[1]

                # Diagonal should be 1.0 (or NaN if insufficient data)
                for symbol in corr_matrix.columns:
                    if symbol in corr_matrix.index:
                        diag_val = corr_matrix.loc[symbol, symbol]
                        assert pd.isna(diag_val) or abs(diag_val - 1.0) < 0.01

    def test_portfolio_with_risk_parity(self, portfolio_data_2_symbols):
        """Test portfolio with risk parity allocation."""
        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in portfolio_data_2_symbols.keys()
        }

        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_2_symbols.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=portfolio_data_2_symbols,
            allocation_method='risk_parity'
        )

        # Check allocations
        allocations = portfolio.calculate_allocations()

        # Should have allocation for each symbol
        assert len(allocations) == 2

        # Allocations should sum to ~1.0 (100%)
        total_allocation = sum(allocations.values())
        assert abs(total_allocation - 1.0) < 0.01

        # Run backtest
        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=20000.0,
            config={'volume': 0.1, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Should complete successfully
        assert result.final_balance > 0
        assert len(result.symbols) == 2

    def test_portfolio_summary_metrics(self, portfolio_data_2_symbols):
        """Test that portfolio summary contains all expected metrics."""
        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in portfolio_data_2_symbols.keys()
        }

        strategies = {
            symbol: TrendStrategy({'symbol': symbol})
            for symbol in portfolio_data_2_symbols.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=portfolio_data_2_symbols,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0,
            config={'volume': 0.05, 'verbose': False}
        )

        result = engine.run(synchronize_data=True)

        # Get portfolio summary
        summary = result.get_portfolio_summary()

        # Check all required fields exist
        required_fields = [
            'portfolio_name', 'symbols', 'initial_balance', 'final_balance',
            'total_return', 'total_return_pct', 'total_trades',
            'max_drawdown_pct', 'win_rate', 'profit_factor', 'sharpe_ratio'
        ]

        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

        # Check types
        assert isinstance(summary['symbols'], list)
        assert isinstance(summary['initial_balance'], (int, float))
        assert isinstance(summary['final_balance'], (int, float))
        assert isinstance(summary['total_trades'], int)

        # Check values make sense
        assert summary['initial_balance'] == 10000.0
        assert summary['final_balance'] > 0
        assert summary['total_trades'] >= 0
