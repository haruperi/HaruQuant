"""
Example usage of TradeSimulator.

This example demonstrates:
- Initializing a trading simulator
- Setting magic number and slippage
- Adding a symbol
- Running a bar-by-bar simulation
- Opening and closing positions at specific bars
"""

import sys
import os
from datetime import datetime
import time

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from apps.logger import logger
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from data.strategies.trend_following import TrendFollowingStrategy
from apps.trade import PositionInfo

mt5 = get_mt5_api()



def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("Trade Simulator Example")
    print("=" * 70)
    print()

    # Get credentials and connect to MT5
    creds = get_mt5_credentials()
    client = MT5Client()

    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    # Global variables
    magic_number = 12345
    slippage = 10
    eurusd = "EURUSD"
    volume = 0.1
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31) 
    data_modelling = "real_ticks"       # "real_ticks", "synthetic_ticks", "m1_ohlc", "trading_timeframe"
    step_data = None

    # Initialize AccountInfoSimulator
    account_info = AccountInfoSimulator()

    # Initialize Symbols
    eurusd_info = SymbolInfoSimulator.from_mt5_symbol(eurusd)

    # Initialize TradeSimulator 
    simulator = TradeSimulator(simulator_name="EURUSD_Backtest",mt5_client=client, account_info=account_info, symbols={eurusd: eurusd_info})

    # Trading timeframe data (signals are generated from this)
    data = client.get_bars(symbol=eurusd, timeframe="H1", date_from=start_date, date_to=end_date)
    if data is None or len(data) == 0:
        print("No H1 data available.")
        client.shutdown()
        return

    # M1 data for synthetic and m1_ohlc modeling
    m1_data = client.get_bars(symbol=eurusd, timeframe="M1", date_from=start_date, date_to=end_date)
    if m1_data is None or len(m1_data) == 0:
        print("No M1 data available.")
        client.shutdown()
        return

    # Real ticks for real_ticks modeling
    ticks = client.get_ticks(symbol=eurusd, start=start_date, end=end_date, as_dataframe=True)
    if ticks is None or len(ticks) == 0:
        print("No tick data available.")
        client.shutdown()
        return

    if data_modelling == "real_ticks":
        step_data = ticks
    elif data_modelling == "synthetic_ticks" or data_modelling == "m1_ohlc":
        step_data = m1_data


    # Initialize strategy
    simulator.trade.SetExpertMagicNumber(magic_number)
    simulator.trade.SetDeviationInPoints(slippage)
    strategy = TrendFollowingStrategy(
        params={
            'symbol': eurusd,
            'fast_period': 20,
            'slow_period': 50,
            'filter_period': 200
        }
    )

    strategy.on_init()
    
    # Calculate indicators and signals 
    data = strategy.on_bar(data)
    
    # Run simulation
    backtest_metadata = {
        "strategy_name": "TrendFollowingStrategy",
        "strategy_version": "1.0.0",
        "start_date": datetime(2025, 1, 1),
        "end_date": datetime(2025, 12, 31),
        "engine_type": "simulator",
        "data_resolution": "H1",
        "config_hash": "trend_following_eurusd_h1",
        "data_modelling": data_modelling,
        "symbols": [eurusd],
        "timeframes": ["H1"],
        "initial_balance": account_info.balance,
        "alias": "EURUSD H1 Trend Following",
        "description": "Simulator run with DB save enabled",
    }

    start_time = time.time()
    
    simulator.run(
        data=data,
        strategy=strategy,
        symbol=eurusd,
        volume=volume,
        verbose=True,
        save_db=True,
        metadata=backtest_metadata,
        step_data=step_data,
        data_modelling=data_modelling,
    )

    end_time = time.time()
    print(f"Backtest with {data_modelling} completed in {end_time - start_time:.2f} seconds")
    
    # Disconnect MT5
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
