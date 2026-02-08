"""
Portfolio Backtest Example

Purpose:
- Demonstrate multi-asset portfolio backtesting
- Show portfolio-level risk management
- Calculate portfolio metrics and correlations
- Analyze diversification benefits

Key Concepts:
- Using apps.simulation.portfolio module
- Multi-strategy backtesting
- Portfolio-level metrics
- Correlation analysis

Usage:
    python tests/usage/backtest/07_portfolio_backtest.py

Output:
- Console output with portfolio metrics
- Individual asset performance
- Portfolio-level statistics
- Correlation matrix
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


# Create output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class TrendFollowingStrategy(BaseStrategy):
    """Simple trend following strategy for example."""

    def __init__(self, params=None):
        self.params = params or {}
        self.symbol = self.params.get('symbol', '')
        self.fast_period = self.params.get('fast_period', 20)
        self.slow_period = self.params.get('slow_period', 50)

    def on_init(self) -> None:
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators and generate signals."""
        # Calculate fast and slow moving averages
        data[f'sma_{self.fast_period}'] = data['close'].rolling(window=self.fast_period).mean()
        data[f'sma_{self.slow_period}'] = data['close'].rolling(window=self.slow_period).mean()

        # Generate entry signals
        data['entry_signal'] = 0
        # Buy when fast MA crosses above slow MA
        data.loc[data[f'sma_{self.fast_period}'] > data[f'sma_{self.slow_period}'], 'entry_signal'] = 1
        # Sell when fast MA crosses below slow MA
        data.loc[data[f'sma_{self.fast_period}'] < data[f'sma_{self.slow_period}'], 'entry_signal'] = -1

        data['exit_signal'] = 0

        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Return signal for current bar."""
        if current_index < self.slow_period:
            return None

        entry_signal = int(data.iloc[current_index]['entry_signal'])

        if entry_signal == 0:
            return None

        return {
            'entry_signal': entry_signal,
            'exit_signal': 0,
            'type': 'buy' if entry_signal == 1 else 'sell',
        }


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"
    username = "haruperi"
    user = user_manager.get_user(username=username)
    if not user:
        raise ValueError(f"User {username} not found")
    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        raise ValueError(f"No MT5 credentials found")
    return creds


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Load historical data from MT5."""
    creds = get_mt5_credentials()
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )
    if not connected:
        raise ConnectionError("Failed to connect to MT5")
    df = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
    if df.empty:
        raise ValueError("No data retrieved from MT5")
    return df


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("PORTFOLIO BACKTEST EXAMPLE")
    logger.info("=" * 70)

    # Step 1: Define portfolio assets
    logger.info("\n[1/5] Defining portfolio assets...")

    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    logger.info(f"Portfolio symbols: {symbols}")

    # Step 2: Load data for each asset from MT5
    logger.info("\n[2/5] Loading data from MT5 for each asset...")

    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)

    data_dict = {}
    for symbol in symbols:
        try:
            data = load_mt5_data(symbol, 'H1', date_from, date_to)
            data_dict[symbol] = data
            logger.info(f"  {symbol}: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        except Exception as e:
            logger.warning(f"  {symbol}: Failed to load data - {e}")
            # Use synthetic data as fallback
            logger.info(f"  {symbol}: Using synthetic data instead")
            dates = pd.date_range(date_from, date_to, freq='1h')[:1000]
            prices = 1.1 + np.cumsum(np.random.randn(len(dates)) * 0.0001)
            if 'JPY' in symbol:
                prices = prices * 150
            data_dict[symbol] = pd.DataFrame({
                'open': prices,
                'high': prices * 1.001,
                'low': prices * 0.999,
                'close': prices,
                'volume': 1000
            }, index=dates)

    # Step 3: Create symbol specs (using SymbolInfoSimulator)
    logger.info("\n[3/5] Creating symbol specifications...")

    symbol_specs = {}
    for symbol in symbols:
        symbol_specs[symbol] = SymbolInfoSimulator.from_mt5_symbol(symbol)
        logger.info(f"  {symbol}: Created SymbolInfoSimulator")

    # Step 4: Create strategies for each asset
    logger.info("\n[4/5] Creating strategies...")

    strategies = {}
    for symbol in symbols:
        # Use different parameters for each symbol for diversification
        params = {
            'symbol': symbol,
            'fast_period': 20,
            'slow_period': 50,
        }

        strat = TrendFollowingStrategy(params=params)
        strat.on_init()
        data_dict[symbol] = strat.on_bar(data_dict[symbol])
        strategies[symbol] = strat
        logger.info(f"  {symbol}: TrendFollowingStrategy (fast=20, slow=50) - signals calculated")

    # Create portfolio strategy
    logger.info("\nCreating portfolio strategy...")

    portfolio_strategy = PortfolioStrategy(
        strategies=strategies,
        symbol_specs=symbol_specs,
        data=data_dict,
        max_total_exposure=float(len(symbols)),  # 1.0 per symbol so volume is used as-is
        max_correlated_exposure=0.6,
        allocation_method='equal_weight'
    )

    # Validate portfolio
    portfolio_strategy.validate()
    logger.info("Portfolio strategy validated successfully")

    # Step 5: Run portfolio backtest
    logger.info("\n[5/5] Running portfolio backtest...")
    logger.info("=" * 70)

    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=10000.0,
        config={
            'portfolio_name': 'Multi-Currency Trend Following',
            'volume': 0.01,
            'commission': 7.0,
            'slippage': 0.5,
            'verbose': False
        }
    )

    portfolio_result = portfolio_engine.run(synchronize_data=True, sync_method='ffill')

    logger.info("\nPortfolio backtest completed!")

    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("PORTFOLIO RESULTS")
    logger.info("=" * 70)

    # Portfolio summary
    summary = portfolio_result.get_portfolio_summary()

    logger.info(f"\nPortfolio: {summary['portfolio_name']}")
    logger.info(f"Initial Balance: ${portfolio_result.initial_balance:,.2f}")
    logger.info(f"Final Balance: ${portfolio_result.final_balance:,.2f}")

    logger.info(f"\n--- Portfolio Performance ---")
    logger.info(f"Total Return: ${summary['total_return']:,.2f} ({summary['total_return_pct']:.2f}%)")
    logger.info(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
    logger.info(f"Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Total Trades: {summary['total_trades']}")
    logger.info(f"Win Rate: {summary['win_rate']:.2f}%")
    logger.info(f"Profit Factor: {summary['profit_factor']:.2f}")

    # Individual asset performance
    logger.info(f"\n--- Individual Asset Performance ---")

    for symbol, result in portfolio_result.asset_results.items():
        logger.info(f"\n{symbol}:")
        logger.info(f"  Return: ${result.total_return:,.2f} ({result.total_return_pct:.2f}%)")
        logger.info(f"  Max DD: {result.max_drawdown_pct:.2f}%")
        logger.info(f"  Trades: {result.total_trades}")
        logger.info(f"  Win Rate: {result.win_rate:.2f}%")
        logger.info(f"  Profit Factor: {result.profit_factor:.2f}")

    # Asset contributions
    logger.info(f"\n--- Asset Contributions to Portfolio ---")

    contributions = portfolio_result.get_asset_contributions()
    for symbol, contrib in contributions.items():
        logger.info(f"\n{symbol}:")
        logger.info(f"  Contribution: {contrib['contribution_pct']:.2f}%")
        logger.info(f"  Total Return: ${contrib['total_return']:,.2f}")
        logger.info(f"  Sharpe Ratio: {contrib['sharpe_ratio']:.2f}")

    # Correlation analysis
    logger.info(f"\n--- Correlation Analysis ---")

    correlation_matrix = portfolio_result.get_correlation_matrix()

    if not correlation_matrix.empty:
        logger.info("\nReturns Correlation Matrix:")
        logger.info(correlation_matrix.to_string())

        # Average correlation (excluding diagonal)
        mask = np.ones(correlation_matrix.shape, dtype=bool)
        np.fill_diagonal(mask, False)
        avg_corr = correlation_matrix.values[mask].mean()

        logger.info(f"\nAverage Correlation: {avg_corr:.3f}")

        if avg_corr < 0.3:
            logger.info("Assessment: Good diversification (low correlation)")
        elif avg_corr < 0.6:
            logger.info("Assessment: Moderate diversification")
        else:
            logger.info("Assessment: Poor diversification (high correlation)")
    else:
        logger.info("Not enough trades to calculate correlation matrix")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("PORTFOLIO BACKTEST COMPLETE")
    logger.info("=" * 70)

    logger.info(f"\nKey Findings:")
    logger.info(f"  - Portfolio return: {summary['total_return_pct']:.2f}%")
    logger.info(f"  - Portfolio max drawdown: {summary['max_drawdown_pct']:.2f}%")
    logger.info(f"  - Number of assets: {len(symbols)}")
    logger.info(f"  - Total trades across portfolio: {summary['total_trades']}")

    if not correlation_matrix.empty:
        logger.info(f"  - Average correlation: {avg_corr:.3f}")

    logger.info("\n" + "=" * 70)

    return portfolio_result


if __name__ == "__main__":
    result = main()
