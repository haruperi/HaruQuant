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
from apps.utils.logger import logger


# Create output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class TrendFollowingStrategy(BaseStrategy):
    """
    EMA Crossover Trend Following Strategy (Strategy ID 12 from UI)

    Classic trend following approach using two EMAs to identify trend direction.
    Exit signals are based on EMA crossovers.
    """

    def __init__(self, params=None):
        super().__init__(params)
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 20)
        self.slow_period = self.params.get('slow_period', 50)
        self.filter_period = self.params.get('filter_period', 200)

    def on_init(self) -> None:
        """Initialize strategy."""
        logger.info(f"MA Crossover Strategy initialized for {self.params.get('symbol', 'N/A')}")
        logger.info(f"Parameters: Fast={self.fast_period}, Slow={self.slow_period}, Filter={self.filter_period}")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators and detect EMA crossovers."""
        from apps.indicator import ema

        # Calculate indicators
        data = ema(data, self.fast_period)
        data = ema(data, self.slow_period)
        data = ema(data, self.filter_period)

        # Get column names
        ema_fast_col = f'ema_{self.fast_period}'
        ema_slow_col = f'ema_{self.slow_period}'
        ema_filter_col = f'ema_{self.filter_period}'

        # Shift indicators to use previous bar values
        data[ema_fast_col] = data[ema_fast_col].shift(1)
        data[ema_slow_col] = data[ema_slow_col].shift(1)
        data[ema_filter_col] = data[ema_filter_col].shift(1)

        # Creating prev columns
        data[f'prev_{ema_fast_col}'] = data[ema_fast_col].shift(1)
        data[f'prev_{ema_slow_col}'] = data[ema_slow_col].shift(1)

        # Initialize signal columns
        data['entry_signal'] = 0
        data['exit_signal'] = 0
        data['pending_signal'] = 0
        data['cancel_pending_signal'] = 0
        data['price'] = float('nan')

        # Define Conditions
        condition_1_buy = data[ema_fast_col] > data[ema_slow_col]
        condition_1_sell = data[ema_fast_col] < data[ema_slow_col]
        condition_2_buy = data[f'prev_{ema_fast_col}'] < data[f'prev_{ema_slow_col}']
        condition_2_sell = data[f'prev_{ema_fast_col}'] > data[f'prev_{ema_slow_col}']
        condition_3_buy = data[ema_slow_col] > data[ema_filter_col]
        condition_3_sell = data[ema_slow_col] < data[ema_filter_col]

        # Exit Signals (Cross in opposite direction)
        condition_exit_short = condition_1_buy & condition_2_buy
        data.loc[condition_exit_short, 'exit_signal'] = -1
        data.loc[condition_exit_short, 'price'] = data.loc[condition_exit_short, 'open']

        condition_exit_long = condition_1_sell & condition_2_sell
        data.loc[condition_exit_long, 'exit_signal'] = 1
        data.loc[condition_exit_long, 'price'] = data.loc[condition_exit_long, 'open']

        # Entry Signals
        condition_entry_buy = condition_1_buy & condition_2_buy & condition_3_buy
        data.loc[condition_entry_buy, 'entry_signal'] = 1
        data.loc[condition_entry_buy, 'price'] = data.loc[condition_entry_buy, 'open']

        condition_entry_sell = condition_1_sell & condition_2_sell & condition_3_sell
        data.loc[condition_entry_sell, 'entry_signal'] = -1
        data.loc[condition_entry_sell, 'price'] = data.loc[condition_entry_sell, 'open']

        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Get signal details for a specific bar."""
        row = data.iloc[current_index]
        entry = row['entry_signal']
        exit_sig = row['exit_signal']

        if entry == 0 and exit_sig == 0:
            return None

        bar = data.iloc[current_index]
        entry_price = bar["price"]
        reason = None
        entry_signal = 0
        exit_signal = 0

        if entry == 1:
            reason = f"Fast({self.fast_period}) crossed above Slow({self.slow_period}) > Filter({self.filter_period})"
            entry_signal = 1
        elif entry == -1:
            reason = f"Fast({self.fast_period}) crossed below Slow({self.slow_period}) < Filter({self.filter_period})"
            entry_signal = -1

        if exit_sig == 1:
            reason = f"Close Buy: Bearish Crossover" if not reason else reason + " | Close Buy"
            exit_signal = 1
        elif exit_sig == -1:
            reason = f"Close Sell: Bullish Crossover" if not reason else reason + " | Close Sell"
            exit_signal = -1

        return {
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "time": bar.name,
            "reason": reason,
            "price": entry_price,
            "stop_loss": None,
            "take_profit": None,
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
    logger.info("PORTFOLIO BACKTEST EXAMPLE - TERMINAL")
    logger.info("=" * 70)

    # Step 1: Define portfolio assets
    logger.info("\n[1/6] Defining portfolio assets...")

    symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
    logger.info(f"Portfolio symbols: {symbols}")

    # Step 2: Load data for each asset from MT5
    logger.info("\n[2/6] Loading data from MT5 for each asset...")

    # Warmup period: 1 Dec 2024 to allow indicators to warm up
    warmup_date = datetime(2024, 12, 1)
    # Trading period: 1 Jan 2025 to 31 Dec 2025
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)

    logger.info(f"Warmup period: {warmup_date.strftime('%Y-%m-%d')} onwards")
    logger.info(f"Trading period: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}")

    data_dict = {}
    for symbol in symbols:
        # Load data from warmup date for indicator calculation
        data = load_mt5_data(symbol, 'H1', warmup_date, date_to)
        data_dict[symbol] = data
        logger.info(f"  {symbol}: {len(data)} bars from {data.index[0]} to {data.index[-1]}")

    # Step 3: Create symbol specs (using SymbolInfoSimulator)
    logger.info("\n[3/6] Creating symbol specifications...")

    symbol_specs = {}
    for symbol in symbols:
        symbol_specs[symbol] = SymbolInfoSimulator.from_mt5_symbol(symbol)
        logger.info(f"  {symbol}: Created SymbolInfoSimulator")

    # Step 4: Create strategies for each asset
    logger.info("\n[4/6] Creating strategies...")

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
    logger.info("\n[5/6] Running portfolio backtest...")
    logger.info("=" * 70)

    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=10000.0,
        config={
            'portfolio_name': 'Multi-Currency Trend Following',
            'volume': 0.03,  # Fixed lot size (matching UI)
            'commission': 7.0,  # $7 per contract
            'slippage': 0.0,  # Fixed slippage, 0 points
            'slippage_type': 'fixed',
            'leverage': 400,  # Leverage 400
            'start_date': date_from,  # Trading period start (excluding warmup)
            'end_date': date_to,  # Trading period end
            'verbose': False
        }
    )

    logger.info("\nBacktest Configuration:")
    logger.info(f"  Initial Balance: $10,000")
    logger.info(f"  Volume: 0.03 lots per symbol (matching UI)")
    logger.info(f"  Commission: $7.0 per contract (round-trip)")
    logger.info(f"  Slippage: 0 points (fixed)")
    logger.info(f"  Leverage: 400:1")
    logger.info(f"  Spread: Using broker data")
    logger.info(f"  Engine: Event-driven")

    portfolio_result = portfolio_engine.run(synchronize_data=True, sync_method='ffill')

    logger.info("\nPortfolio backtest completed!")

    # Step 6: Save results to database
    logger.info("\n[6/6] Saving results to database...")

    from apps.sqlite.backtests import BacktestManager
    from apps.sqlite.database_operations import DatabaseManager

    db_manager = DatabaseManager()
    backtest_manager = BacktestManager()
    backtest_manager.db_path = db_manager.db_path

    # Create backtest run record
    backtest_id = backtest_manager.create_backtest_run(
        strategy_name="Multi-Currency Trend Following",
        strategy_version="1.0.0",
        start_date=date_from,
        end_date=date_to,
        engine_type="event_driven",
        data_resolution="trading_timeframe",
        config_hash=str(hash(("portfolio", tuple(symbols), "H1"))),
        symbols=symbols,
        timeframes=["H1"] * len(symbols),
        initial_balance=10000.0,
        alias="Multi-Symbol-terminal",
        description="Portfolio backtest run from terminal script with warmup period",
        strategy_version_id=None,  # No specific strategy version for this example
        user_id=1,  # Default user
    )

    logger.info(f"  Created backtest run with ID: {backtest_id}")

    # Save trades to database
    if portfolio_result.trades:
        backtest_manager.save_backtest_trades(backtest_id, portfolio_result.trades)
        logger.info(f"  Saved {len(portfolio_result.trades)} trades to database")
    else:
        logger.warning("  No trades to save")

    # Update backtest status with final balance
    backtest_manager.update_backtest_status(
        backtest_id,
        "completed",
        final_balance=float(portfolio_result.final_balance),
    )

    logger.info(f"  Backtest status updated to 'completed'")
    logger.info(f"  Database saved with alias: 'Multi-Symbol-terminal'")
    logger.info(f"  Backtest ID: {backtest_id}")

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

