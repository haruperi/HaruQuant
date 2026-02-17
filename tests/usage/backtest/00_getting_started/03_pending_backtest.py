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
from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator
from data.strategies.breakout import BreakoutStrategy
from apps.finance import metrics, ratios, drawdowns, risks, returns, efficiency, distributions
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger


def get_mt5_client():
    """Get a connected MT5 client."""
    creds = UserManager().get_mt5_credentials()
    client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise ConnectionError("Failed to connect to MT5")
    return client


def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Load historical data from MT5."""
    client = get_mt5_client()
    try:
        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )

        if df is None or df.empty:
            raise ValueError("No data retrieved from MT5")

        return df
    finally:
        client.shutdown()


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

    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance=10000.0,
        equity=10000.0,
        margin_free=10000.0,
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('EURUSD')
    symbol_info.symbol = 'EURUSD'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="PendingOrders_Backtest",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=7.0,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)
    logger.info(f"Backtest completed: {result.total_trades} trades executed")
    
    # Step 2: Calculate metrics
    logger.info("\n[2/3] Calculating comprehensive metrics...")

    # Get trades DataFrame
    trades_df = result.get_trades_df()
    if trades_df.empty:
        logger.warning("No trades executed, metrics will be limited")
    
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

    # Cleanup
    mt5_client.shutdown()

    return result

if __name__ == "__main__":
    result = main()

