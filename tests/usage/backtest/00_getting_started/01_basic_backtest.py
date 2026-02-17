"""
Basic Backtest Example using TradeSimulator

Purpose:
- Demonstrate the simplest possible backtest workflow using the modern TradeSimulator
- Show how to initialize a strategy with parameters
- Run an event-driven backtest
- Access and display basic results

Key Concepts:
- TradeSimulator initialization
- Strategy initialization with params dict
- Backtest execution with explicit data loading
- Result extraction from Simulator state

Usage:
    python tests/usage/backtest/00_getting_started/01_basic_backtest.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from data.strategies.trend_following import TrendFollowingStrategy

def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds

def calculate_metrics(account: AccountInfoSimulator, completed_trades: list) -> dict:
    """Calculate basic performance metrics from simulation results."""
    
    total_trades = len(completed_trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_profit": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0
        }

    winning_trades = [t for t in completed_trades if t.profit_loss > 0]
    losing_trades = [t for t in completed_trades if t.profit_loss <= 0]
    
    gross_profit = sum(t.profit_loss for t in winning_trades)
    gross_loss = abs(sum(t.profit_loss for t in losing_trades))
    
    win_rate = (len(winning_trades) / total_trades) * 100
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    return {
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_profit": account.balance - 10000.0, # Total Realized Profit (assuming 10k initial)
        "equity": account.equity,
        "balance": account.balance
    }

def main():
    logger.info("=" * 70)
    logger.info("BASIC BACKTEST EXAMPLE (TradeSimulator)")
    logger.info("=" * 70)

    # 1. Configuration
    symbol = "EURUSD"
    timeframe = "H1"

    # Warmup period configuration (similar to MT5 Strategy Tester):
    # - warmup_start_date: Start downloading data from this date (for indicator warmup)
    # - start_date: Start executing trades from this date (active trading period begins)
    # - end_date: Stop executing trades after this date (active trading period ends)
    warmup_start_date = datetime(2024, 10, 1)  # 3 months of warmup data
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)

    initial_balance = 10000.0
    slippage = 10
    commission_per_contract = 0.0
    
    # 2. Connect to MT5
    logger.info("\n[1/5] Connecting to MT5...")
    creds = get_mt5_credentials()
    client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        logger.error("Failed to connect to MT5")
        return

    try:
        # 3. Initialize Simulator Components
        logger.info("\n[2/5] Initializing Simulator...")
        
        # Account
        account_info = AccountInfoSimulator(
            balance=initial_balance,
            leverage=100.0,
            currency="USD"
        )
        
        # Symbol
        symbol_info = SymbolInfoSimulator.from_mt5_symbol(symbol)
        
        # Simulator Engine
        simulator = TradeSimulator(
            simulator_name="Basic_Backtest",
            mt5_client=client,
            account_info=account_info,
            symbols={symbol: symbol_info}
        )
        
        # 4. Load Data
        logger.info("\n[3/5] Loading historical data...")
        # Load data from warmup_start_date to properly initialize indicators
        data = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=warmup_start_date,
            date_to=end_date
        )
        
        if data is None or data.empty:
            logger.error("No data retrieved.")
            return
            
        logger.info(f"Loaded {len(data)} bars")

        # 5. Setup Strategy
        logger.info("\n[4/5] Setting up strategy...")
        simulator.trade.SetExpertMagicNumber(123456)
        
        strategy = TrendFollowingStrategy(
            params={
                'symbol': symbol,
                'fast_period': 20,
                'slow_period': 50,
                'filter_period': 200
            }
        )
        strategy.on_init()
        # Pre-calculate signals (Vectorized/Pandas approach used by Strategy class)
        data = strategy.on_bar(data)

        # 6. Run Simulation
        logger.info("\n[5/5] Running simulation...")
        start_time = time.time()
        
        simulator.run(
            data=data,
            strategy=strategy,
            symbol=symbol,
            volume=0.1,
            verbose=False, # Set to True for bar-by-bar logs
            save_db=False,
            engine_type="event_driven",
            commission_per_contract=commission_per_contract,
            slippage_points=slippage,
            start_date=start_date,  # Trading starts here (after warmup)
            end_date=end_date,      # Trading ends here
        )
        
        duration = time.time() - start_time
        logger.info(f"Simulation finished in {duration:.2f} seconds")
        
        # 7. Results
        logger.info("\n" + "=" * 70)
        logger.info("RESULTS SUMMARY")
        logger.info("=" * 70)
        
        trades = simulator._completed_trades
        metrics = calculate_metrics(account_info, trades)
        
        logger.info(f"Final Balance: ${metrics['balance']:,.2f}")
        logger.info(f"Final Equity:  ${metrics['equity']:,.2f}")
        logger.info(f"Total Return:  ${metrics['balance'] - initial_balance:,.2f} ({((metrics['balance'] - initial_balance)/initial_balance)*100:.2f}%)")
        logger.info("-" * 30)
        logger.info(f"Total Trades:    {metrics['total_trades']}")
        logger.info(f"Winning Trades:  {metrics['winning_trades']}")
        logger.info(f"Losing Trades:   {metrics['losing_trades']}")
        logger.info(f"Win Rate:        {metrics['win_rate']:.2f}%")
        logger.info(f"Profit Factor:   {metrics['profit_factor']:.2f}")
        
        if trades:
            logger.info("\nFirst Trade:")
            first = trades[0]
            logger.info(f"  {first.type} {first.size} {first.symbol} @ {first.open_price:.5f} -> {first.close_price:.5f} | P/L: ${first.profit_loss:.2f}")
            
            logger.info("\nLast Trade:")
            last = trades[-1]
            logger.info(f"  {last.type} {last.size} {last.symbol} @ {last.open_price:.5f} -> {last.close_price:.5f} | P/L: ${last.profit_loss:.2f}")

    finally:
        client.shutdown()
        logger.info("\nMT5 Connection closed.")

if __name__ == "__main__":
    main()

