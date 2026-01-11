"""
Pending Orders Backtest Example.

Purpose:
- Demonstrate BreakoutStrategy using newly implemented Pending Orders
- Verify pending entries (Buy Stop / Sell Stop)
- Show comprehensive metrics for a Breakout system

Usage:
    python tests/usage/backtest/00_getting_started/03_pending_backtest.py

Output:
- Detailed console output with all calculated metrics
- Trade list showing Stop Order executions
"""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from apps.backtest import EventDrivenEngine
from data.strategies.breakout import BreakoutStrategy
from apps.finance import metrics, ratios, drawdowns, risks, returns, efficiency, distributions
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


def get_mt5_client():
    """Get a connected MT5 client."""
    creds = UserManager().get_mt5_credentials()
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )
    return client


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Load historical data from MT5."""
    with get_mt5_client() as client:
        if not client.is_connected():
            raise ConnectionError("Failed to connect to MT5")

        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )

        if df.empty:
            raise ValueError("No data retrieved from MT5")

        return df


def print_section(title: str):
    """Print a formatted section header."""
    logger.info(f"\n{'=' * 70}")
    logger.info(f"{title:^70}")
    logger.info(f"{'=' * 70}")


def print_metric(name: str, value, unit: str = ""):
    """Print a formatted metric."""
    if isinstance(value, float):
        if unit == "%":
            logger.info(f"  {name:<35} {value:>10.2f}{unit}")
        elif unit == "$":
            logger.info(f"  {name:<35} {unit}{value:>10,.2f}")
        else:
            logger.info(f"  {name:<35} {value:>10.4f}{unit}")
    else:
        logger.info(f"  {name:<35} {value:>10}{unit}")


def main():
    """Main execution function."""
    print_section("PENDING ORDERS BACKTEST (BREAKOUT STRATEGY)")
    
    # Step 1: Load data and run backtest
    logger.info("\n[1/3] Loading data from MT5...")
    
    # Backtest period
    backtest_start = datetime(2025, 1, 1)
    backtest_end = datetime(2025, 12, 31)
    
    # Add warm-up period
    warmup_bars = 250
    warmup_hours = warmup_bars
    warmup_days = warmup_hours / 24
    
    # Calculate data load start date
    from datetime import timedelta
    data_load_start = backtest_start - timedelta(days=warmup_days + 5)
    
    logger.info(f"Backtest period: {backtest_start.date()} to {backtest_end.date()}")
    logger.info(f"Loading data from: {data_load_start.date()}")
    
    # Load data
    try:
        data = load_mt5_data('EURUSD', 'D1', data_load_start, backtest_end)
        logger.info(f"Loaded {len(data)} bars")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return
    
    logger.info("\nRunning backtest...")
    
    # Use BreakoutStrategy
    strategy = BreakoutStrategy(params={
        'symbol': 'EURUSD',
        'timeframe': 'D1'
    })

    # Get MT5 client for symbol info
    try:
        mt5_client = get_mt5_client()
    except Exception as e:
        logger.warning(f"Could not connect to MT5 for symbol info: {e}")
        mt5_client = None

    engine = EventDrivenEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=7.0,
        slippage_points=0,
        backtest_start_date=backtest_start,
        backtest_end_date=backtest_end,
        timeframe='D1',
        mt5_client=mt5_client
    )
    
    result = engine.run()
    logger.info(f"Backtest completed: {result.total_trades} trades executed")
    
    # Step 2: Calculate metrics
    logger.info("\n[2/3] Calculating comprehensive metrics...")
    
    if len(result.trades) > 0:
        trades_df = pd.DataFrame([t.to_dict() for t in result.trades])
    else:
        logger.warning("No trades executed, metrics will be limited")
        trades_df = pd.DataFrame()
    
    equity_series = result._get_equity_series()
    returns_series = result._get_returns_series()
    
    # Step 3: Display all metrics
    logger.info("\n[3/3] Displaying metrics by category...")
    
    # RETURN METRICS
    print_section("RETURN METRICS")
    print_metric("Total Return", result.total_return, "$")
    print_metric("Total Return %", result.total_return_pct, "%")
    
    if len(equity_series) > 0:
        cagr = returns.cagr(equity_series)
        print_metric("CAGR", cagr, "%")
    
    # RATIOS
    print_section("RISK-ADJUSTED RATIOS")
    if len(returns_series) > 0:
        sharpe = ratios.sharpe_ratio(returns_series, risk_free_rate=0.0)
        sortino = ratios.sortino_ratio(returns_series, target_return=0.0)
        print_metric("Sharpe Ratio", sharpe)
        print_metric("Sortino Ratio", sortino)
        
    # DRAWDOWN
    print_section("DRAWDOWN METRICS")
    print_metric("Max Drawdown", result.max_drawdown, "$")
    print_metric("Max Drawdown %", result.max_drawdown_pct, "%")
    
    # TRADE METRICS
    print_section("TRADE METRICS")
    print_metric("Total Trades", result.total_trades)
    print_metric("Win Rate", result.win_rate, "%")
    print_metric("Profit Factor", result.profit_factor)
    
    # TRADES LIST
    trades_df = result.get_trades_df()
    print_section("Backtest Trades")
    
    if len(trades_df) > 0:
        # Updated header with new columns
        header = f"{'Type':<6} {'Entry Date':<19} {'Exit Date':<19} {'Entry':>9} {'Exit':>9} {'Size':>6} {'Comm':>8} {'Swap':>8} {'Gross $':>10} {'Net $':>10} {'Pips':>8} {'Duration':>8}"
        logger.info("-" * len(header))
        logger.info(header)
        logger.info("-" * len(header))
        
        for _, trade in trades_df.head(50).iterrows():
            direction = str(trade.get('type', 'UNKNOWN')).upper()
            # Truncate microseconds for cleaner output if needed, or keeping standard str
            entry_time = str(trade.get('open_time', ''))[:19]
            exit_time = str(trade.get('close_time', ''))[:19]
            entry_price = trade.get('open_price', 0.0)
            exit_price = trade.get('close_price', 0.0)
            size = trade.get('size', 0.0)
            
            comm = trade.get('commission', 0.0)
            swap = trade.get('swap', 0.0)
            net_pnl = trade.get('profit_loss', 0.0)
            
            # Calculate Gross P&L: Net = Gross + Comm + Swap => Gross = Net - Comm - Swap
            gross_pnl = net_pnl - comm - swap
            
            pnl_pips = trade.get('profit_loss_pips', 0.0)
            duration = trade.get('time_in_trade', 0.0)

            row = f"{direction:<6} {entry_time:<19} {exit_time:<19} {entry_price:>9.5f} {exit_price:>9.5f} {size:>6.2f} {comm:>8.2f} {swap:>8.2f} {gross_pnl:>10.2f} {net_pnl:>10.2f} {pnl_pips:>8.1f} {duration:>7.1f}h"
            logger.info(row)
            
        if len(trades_df) > 50:
            logger.info(f"... and {len(trades_df) - 50} more trades ...")

    return result

if __name__ == "__main__":
    result = main()
