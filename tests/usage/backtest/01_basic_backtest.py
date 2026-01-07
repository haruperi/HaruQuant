"""
Basic Backtest Example

Purpose:
- Demonstrate the simplest possible backtest workflow
- Show how to initialize a strategy with parameters
- Run an event-driven backtest
- Access and display basic results

Key Concepts:
- Strategy initialization with params dict
- EventDrivenEngine creation and execution
- BacktestResult access and summary

Usage:
    python tests/usage/backtest/01_basic_backtest.py

Output:
- Console output with backtest summary
- Basic performance metrics
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import EventDrivenEngine
from data.strategies.trend_following import TrendFollowingStrategy
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"  # Change this to your username
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        raise ValueError(f"User {username} not found")

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        raise ValueError(f"No MT5 credentials found for {username}")

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")
    return creds


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """
    Load historical data from MT5.
    
    Args:
        symbol: Trading symbol (e.g., 'EURUSD')
        timeframe: Timeframe (e.g., 'H1', 'D1')
        date_from: Start date
        date_to: End date
    
    Returns:
        DataFrame with OHLC data and DatetimeIndex
    """
    creds = get_mt5_credentials()
    
    with MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ) as client:
        if not client.is_connected():
            logger.error("Failed to connect to MT5")
            raise ConnectionError("Failed to connect to MT5")
        
        logger.info(f"Loading {symbol} {timeframe} data from {date_from} to {date_to}")
        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )
        
        if df.empty:
            logger.error("No data retrieved from MT5")
            raise ValueError("No data retrieved from MT5")
        
        logger.info(f"Loaded {len(df)} bars")
        return df


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("BASIC BACKTEST EXAMPLE")
    logger.info("=" * 70)
    
    # Step 1: Load data from MT5
    logger.info("\n[1/4] Loading data from MT5...")
    
    # Date range: 01/01/2025 to 31/12/2025
    date_from = datetime(2025, 1, 1)
    date_to = datetime(2025, 12, 31)
    
    data = load_mt5_data(
        symbol='EURUSD',
        timeframe='H1',
        date_from=date_from,
        date_to=date_to
    )
    logger.info(f"Loaded {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    
    # Step 2: Configure strategy
    logger.info("\n[2/4] Configuring strategy...")
    strategy = TrendFollowingStrategy(params={
        'symbol': 'EURUSD',
        'fast_period': 20,
        'slow_period': 50,
        'filter_period': 200
    })
    logger.info(f"Strategy: {strategy.__class__.__name__}")
    logger.info(f"Parameters: Fast={strategy.fast_period}, Slow={strategy.slow_period}, Filter={strategy.filter_period}")
    
    # Step 3: Run backtest
    logger.info("\n[3/4] Running backtest...")
    engine = EventDrivenEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=7.0,  # $7 per trade
        slippage_points=1.0,  # 1 point slippage
        timeframe='H1'
    )
    
    result = engine.run()
    logger.info("Backtest completed!")
    
    # Step 4: Display results
    logger.info("\n[4/4] Results Summary")
    logger.info("=" * 70)
    
    # Basic metrics
    logger.info(f"\nStrategy: {result.strategy_name}")
    logger.info(f"Symbol: {result.symbol}")
    logger.info(f"Timeframe: {result.timeframe}")
    logger.info(f"Period: {result.start_date} to {result.end_date}")
    logger.info(f"Initial Balance: ${result.initial_balance:,.2f}")
    logger.info(f"Final Balance: ${result.final_balance:,.2f}")
    
    # Performance
    logger.info(f"\n--- Performance ---")
    logger.info(f"Total Return: ${result.total_return:,.2f} ({result.total_return_pct:.2f}%)")
    logger.info(f"Max Drawdown: ${result.max_drawdown:,.2f} ({result.max_drawdown_pct:.2f}%)")
    
    # Trade statistics
    logger.info(f"\n--- Trade Statistics ---")
    logger.info(f"Total Trades: {result.total_trades}")
    logger.info(f"Winning Trades: {result.winning_trades}")
    logger.info(f"Losing Trades: {result.losing_trades}")
    logger.info(f"Win Rate: {result.win_rate:.2f}%")
    logger.info(f"Profit Factor: {result.profit_factor:.2f}")
    
    # Average trade
    logger.info(f"\n--- Average Trade ---")
    logger.info(f"Average Win: ${result.avg_win:,.2f}")
    logger.info(f"Average Loss: ${result.avg_loss:,.2f}")
    logger.info(f"Expectancy: ${result.expectancy:,.2f}")
    
    logger.info("\n" + "=" * 70)
    logger.info("BACKTEST COMPLETE")
    logger.info("=" * 70)
    
    # Show how to access individual trades
    if len(result.trades) > 0:
        logger.info(f"\nFirst trade details:")
        first_trade = result.trades[0]
        logger.info(f"  Entry: {first_trade.open_time} @ ${first_trade.open_price:.5f}")
        logger.info(f"  Exit: {first_trade.close_time} @ ${first_trade.close_price:.5f}")
        logger.info(f"  Direction: {first_trade.type}")
        logger.info(f"  P&L: ${first_trade.profit_loss:.2f}")
        logger.info(f"  Duration: {first_trade.time_in_trade:.2f} hours")
    
    return result


if __name__ == "__main__":
    result = main()
