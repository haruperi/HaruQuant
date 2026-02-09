"""
Unit tests for Portfolio Result classes.

Tests AssetBacktestResult and PortfolioBacktestResult.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from apps.simulation.portfolio_result import AssetBacktestResult, PortfolioBacktestResult
from apps.simulation.records import TradeRecord


@pytest.fixture
def sample_trades_eurusd():
    """Sample trades for EURUSD."""
    base_time = datetime(2024, 1, 1, 10, 0)
    return [
        TradeRecord(
            ticket=1,
            symbol='EURUSD',
            type='buy',
            open_time=base_time,
            close_time=base_time + timedelta(hours=1),
            open_price=1.1000,
            close_price=1.1050,
            size=1.0,
            profit_loss=500.0,
            commission=-7.0,
            swap=0.0,
            setup_id='1'
        ),
        TradeRecord(
            ticket=2,
            symbol='EURUSD',
            type='sell',
            open_time=base_time + timedelta(hours=2),
            close_time=base_time + timedelta(hours=3),
            open_price=1.1050,
            close_price=1.1080,
            size=1.0,
            profit_loss=-300.0,
            commission=-7.0,
            swap=0.0,
            setup_id='2'
        ),
        TradeRecord(
            ticket=3,
            symbol='EURUSD',
            type='buy',
            open_time=base_time + timedelta(hours=4),
            close_time=base_time + timedelta(hours=5),
            open_price=1.1080,
            close_price=1.1120,
            size=1.0,
            profit_loss=400.0,
            commission=-7.0,
            swap=0.0,
            setup_id='3'
        ),
    ]


@pytest.fixture
def sample_trades_gbpusd():
    """Sample trades for GBPUSD."""
    base_time = datetime(2024, 1, 1, 10, 0)
    return [
        TradeRecord(
            ticket=4,
            symbol='GBPUSD',
            type='buy',
            open_time=base_time + timedelta(hours=1),
            close_time=base_time + timedelta(hours=2),
            open_price=1.2500,
            close_price=1.2550,
            size=1.0,
            profit_loss=500.0,
            commission=-7.0,
            swap=0.0,
            setup_id='4'
        ),
        TradeRecord(
            ticket=5,
            symbol='GBPUSD',
            type='sell',
            open_time=base_time + timedelta(hours=3),
            close_time=base_time + timedelta(hours=4),
            open_price=1.2550,
            close_price=1.2520,
            size=1.0,
            profit_loss=300.0,
            commission=-7.0,
            swap=0.0,
            setup_id='5'
        ),
    ]


@pytest.fixture
def sample_equity_curve():
    """Sample equity curve."""
    dates = pd.date_range('2024-01-01', periods=10, freq='1h')
    # Simulate growing equity with some drawdown
    equity = [10000, 10100, 10050, 10200, 10150, 10300, 10250, 10400, 10500, 10600]
    return pd.Series(equity, index=dates)


class TestAssetBacktestResult:
    """Test suite for AssetBacktestResult class."""

    def test_asset_result_creation(self):
        """Test creating AssetBacktestResult."""
        result = AssetBacktestResult(
            symbol='EURUSD',
            total_trades=10,
            total_return=1000.0,
            total_return_pct=10.0,
            max_drawdown_pct=5.0,
            win_rate=60.0,
            profit_factor=2.0,
            sharpe_ratio=1.5
        )

        assert result.symbol == 'EURUSD'
        assert result.total_trades == 10
        assert result.total_return == 1000.0
        assert result.win_rate == 60.0

    def test_asset_result_to_dict(self):
        """Test converting AssetBacktestResult to dict."""
        result = AssetBacktestResult(
            symbol='EURUSD',
            total_trades=10,
            total_return=1000.0,
            total_return_pct=10.0,
            max_drawdown_pct=5.0,
            win_rate=60.0,
            profit_factor=2.0,
            sharpe_ratio=1.5
        )

        result_dict = result.to_dict()

        assert result_dict['symbol'] == 'EURUSD'
        assert result_dict['total_trades'] == 10
        assert result_dict['total_return'] == 1000.0

    def test_get_returns_series(self, sample_trades_eurusd):
        """Test getting returns series from trades."""
        result = AssetBacktestResult(
            symbol='EURUSD',
            total_trades=3,
            total_return=600.0,
            total_return_pct=6.0,
            max_drawdown_pct=3.0,
            win_rate=66.67,
            profit_factor=3.0,
            sharpe_ratio=1.2,
            trades=sample_trades_eurusd
        )

        returns = result._get_returns_series()

        assert len(returns) == 3
        assert returns.iloc[0] == 500.0  # First trade profit
        assert returns.iloc[1] == -300.0  # Second trade loss

    def test_get_returns_series_empty(self):
        """Test getting returns series with no trades."""
        result = AssetBacktestResult(
            symbol='EURUSD',
            total_trades=0,
            total_return=0.0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            sharpe_ratio=0.0,
            trades=[]
        )

        returns = result._get_returns_series()

        assert returns.empty


class TestPortfolioBacktestResult:
    """Test suite for PortfolioBacktestResult class."""

    def test_portfolio_result_creation(self, sample_equity_curve):
        """Test creating PortfolioBacktestResult."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=5,
                total_return=500.0,
                total_return_pct=5.0,
                max_drawdown_pct=2.0,
                win_rate=60.0,
                profit_factor=2.0,
                sharpe_ratio=1.5
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=['EURUSD'],
            initial_balance=10000.0,
            final_balance=10500.0,
            trades=[],
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        assert result.portfolio_name == 'Test Portfolio'
        assert result.symbols == ['EURUSD']
        assert result.initial_balance == 10000.0
        assert result.final_balance == 10500.0

    def test_get_portfolio_summary(self, sample_trades_eurusd, sample_equity_curve):
        """Test portfolio summary calculation."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=3,
                total_return=600.0,
                total_return_pct=6.0,
                max_drawdown_pct=3.0,
                win_rate=66.67,
                profit_factor=3.0,
                sharpe_ratio=1.2,
                trades=sample_trades_eurusd
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=['EURUSD'],
            initial_balance=10000.0,
            final_balance=10600.0,
            trades=sample_trades_eurusd,
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        summary = result.get_portfolio_summary()

        assert summary['portfolio_name'] == 'Test Portfolio'
        assert summary['initial_balance'] == 10000.0
        assert summary['final_balance'] == 10600.0
        assert summary['total_return'] == 600.0
        assert summary['total_return_pct'] == 6.0
        assert summary['total_trades'] == 3
        assert summary['win_rate'] == pytest.approx(66.67, rel=0.1)

    def test_get_asset_contributions_single_asset(self, sample_trades_eurusd, sample_equity_curve):
        """Test asset contributions with single asset."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=3,
                total_return=600.0,
                total_return_pct=6.0,
                max_drawdown_pct=3.0,
                win_rate=66.67,
                profit_factor=3.0,
                sharpe_ratio=1.2,
                trades=sample_trades_eurusd
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=['EURUSD'],
            initial_balance=10000.0,
            final_balance=10600.0,
            trades=sample_trades_eurusd,
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        contributions = result.get_asset_contributions()

        assert 'EURUSD' in contributions
        assert contributions['EURUSD']['total_return'] == 600.0
        assert contributions['EURUSD']['contribution_pct'] == 100.0
        assert contributions['EURUSD']['total_trades'] == 3

    def test_get_asset_contributions_multiple_assets(self, sample_trades_eurusd, sample_trades_gbpusd, sample_equity_curve):
        """Test asset contributions with multiple assets."""
        all_trades = sample_trades_eurusd + sample_trades_gbpusd

        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=3,
                total_return=600.0,
                total_return_pct=6.0,
                max_drawdown_pct=3.0,
                win_rate=66.67,
                profit_factor=3.0,
                sharpe_ratio=1.2,
                trades=sample_trades_eurusd
            ),
            'GBPUSD': AssetBacktestResult(
                symbol='GBPUSD',
                total_trades=2,
                total_return=800.0,
                total_return_pct=8.0,
                max_drawdown_pct=2.0,
                win_rate=100.0,
                profit_factor=float('inf'),
                sharpe_ratio=2.0,
                trades=sample_trades_gbpusd
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Multi-Asset Portfolio',
            symbols=['EURUSD', 'GBPUSD'],
            initial_balance=10000.0,
            final_balance=11400.0,  # 600 + 800
            trades=all_trades,
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        contributions = result.get_asset_contributions()

        assert len(contributions) == 2
        assert 'EURUSD' in contributions
        assert 'GBPUSD' in contributions

        # EURUSD contributed 600/1400 = 42.86%
        assert contributions['EURUSD']['contribution_pct'] == pytest.approx(42.86, rel=0.1)
        # GBPUSD contributed 800/1400 = 57.14%
        assert contributions['GBPUSD']['contribution_pct'] == pytest.approx(57.14, rel=0.1)

    def test_get_correlation_matrix(self, sample_trades_eurusd, sample_trades_gbpusd, sample_equity_curve):
        """Test correlation matrix calculation."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=3,
                total_return=600.0,
                total_return_pct=6.0,
                max_drawdown_pct=3.0,
                win_rate=66.67,
                profit_factor=3.0,
                sharpe_ratio=1.2,
                trades=sample_trades_eurusd
            ),
            'GBPUSD': AssetBacktestResult(
                symbol='GBPUSD',
                total_trades=2,
                total_return=800.0,
                total_return_pct=8.0,
                max_drawdown_pct=2.0,
                win_rate=100.0,
                profit_factor=float('inf'),
                sharpe_ratio=2.0,
                trades=sample_trades_gbpusd
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Multi-Asset Portfolio',
            symbols=['EURUSD', 'GBPUSD'],
            initial_balance=10000.0,
            final_balance=11400.0,
            trades=sample_trades_eurusd + sample_trades_gbpusd,
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        corr_matrix = result.get_correlation_matrix()

        # Should have 2x2 matrix
        assert corr_matrix.shape == (2, 2)
        assert 'EURUSD' in corr_matrix.columns
        assert 'GBPUSD' in corr_matrix.columns

        # Diagonal should be 1.0 (correlation with self)
        assert corr_matrix.loc['EURUSD', 'EURUSD'] == pytest.approx(1.0, abs=0.01)
        assert corr_matrix.loc['GBPUSD', 'GBPUSD'] == pytest.approx(1.0, abs=0.01)

    def test_get_correlation_matrix_empty(self, sample_equity_curve):
        """Test correlation matrix with no trades."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=0,
                total_return=0.0,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                trades=[]
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Empty Portfolio',
            symbols=['EURUSD'],
            initial_balance=10000.0,
            final_balance=10000.0,
            trades=[],
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        corr_matrix = result.get_correlation_matrix()

        # Should be empty
        assert corr_matrix.empty

    def test_calculate_max_drawdown(self, sample_equity_curve):
        """Test max drawdown calculation."""
        asset_results = {}

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=[],
            initial_balance=10000.0,
            final_balance=10600.0,
            trades=[],
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        max_dd = result._calculate_max_drawdown()

        # Equity goes: 10000 → 10100 → 10050 (drawdown from 10100)
        # Max drawdown should be around (10100-10050)/10100 = 0.495%
        assert max_dd > 0
        assert max_dd < 5.0  # Should be less than 5%

    def test_calculate_max_drawdown_empty(self):
        """Test max drawdown with empty equity curve."""
        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=[],
            initial_balance=10000.0,
            final_balance=10000.0,
            trades=[],
            equity_curve=pd.Series(dtype=float),
            asset_results={}
        )

        max_dd = result._calculate_max_drawdown()

        assert max_dd == 0.0

    def test_calculate_sharpe_ratio(self, sample_equity_curve):
        """Test Sharpe ratio calculation."""
        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=[],
            initial_balance=10000.0,
            final_balance=10600.0,
            trades=[],
            equity_curve=sample_equity_curve,
            asset_results={}
        )

        sharpe = result._calculate_sharpe_ratio()

        # Should have positive Sharpe for growing equity
        assert sharpe > 0

    def test_calculate_sharpe_ratio_empty(self):
        """Test Sharpe ratio with empty equity curve."""
        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=[],
            initial_balance=10000.0,
            final_balance=10000.0,
            trades=[],
            equity_curve=pd.Series(dtype=float),
            asset_results={}
        )

        sharpe = result._calculate_sharpe_ratio()

        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_insufficient_data(self):
        """Test Sharpe ratio with insufficient data."""
        equity = pd.Series([10000], index=[datetime(2024, 1, 1)])

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=[],
            initial_balance=10000.0,
            final_balance=10000.0,
            trades=[],
            equity_curve=equity,
            asset_results={}
        )

        sharpe = result._calculate_sharpe_ratio()

        assert sharpe == 0.0

    def test_to_dict(self, sample_trades_eurusd, sample_equity_curve):
        """Test converting PortfolioBacktestResult to dict."""
        asset_results = {
            'EURUSD': AssetBacktestResult(
                symbol='EURUSD',
                total_trades=3,
                total_return=600.0,
                total_return_pct=6.0,
                max_drawdown_pct=3.0,
                win_rate=66.67,
                profit_factor=3.0,
                sharpe_ratio=1.2,
                trades=sample_trades_eurusd
            )
        }

        result = PortfolioBacktestResult(
            portfolio_name='Test Portfolio',
            symbols=['EURUSD'],
            initial_balance=10000.0,
            final_balance=10600.0,
            trades=sample_trades_eurusd,
            equity_curve=sample_equity_curve,
            asset_results=asset_results
        )

        result_dict = result.to_dict()

        assert 'portfolio_summary' in result_dict
        assert 'asset_contributions' in result_dict
        assert 'asset_results' in result_dict
        assert result_dict['portfolio_summary']['portfolio_name'] == 'Test Portfolio'
        assert 'EURUSD' in result_dict['asset_results']
