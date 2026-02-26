"""
Basic backtest scaffold.

Step 01: initialize TradeSimulator only.
"""

import os
import sys
import time
from datetime import datetime
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

import haruquant.core as sim
from apps.utils.logger import logger
from apps.mt5 import MT5Utils, get_mt5_api
from data.strategies.trend_following import TrendFollowingStrategy



def main():
    print("=" * 70)
    print("BASIC BACKTEST EXAMPLE (TradeSimulator)")
    print("=" * 70)

    
    # 1. Configuration
    test_symbol = "XAUUSD"
    audusd = "AUDUSD"
    eurgbp = "EURGBP"
    usdjpy = "USDJPY"
    warmup_start_date = datetime(2024, 10, 1)  # Start downloading data from this date (for indicator warmup)
    start_date = datetime(2025, 1, 1)          # Start date of the backtest
    end_date = datetime(2025, 12, 31)          # End date of the backtest
    timeframe = "H1"                           # Signal Calculation Timeframe





    # Derived globals
    mt5 = get_mt5_api()
    client = MT5Utils.get_connected_client()
    mt5_account = client.account_info()
    test_symbol_info = client.symbol_info(test_symbol)

    account = sim.AccountInfo(mt5_account)     # Get default account info details from MT5
    account.SetServer("Backtest Simulation Server")
    account.SetCompany("HaruQuant")
    account.SetBalance(10000.0)
    account.SetCredit(0.0)
    account.SetProfit(0.0)
    account.SetEquity(10000.0)
    account.SetMargin(0.0)
    account.SetMarginFree(10000.0)
    account.SetMarginLevel(100.0)
    
    simulator = sim.BacktestSimulator(account) # Initialize BacktestSimulator 
    symbol_store = sim.SymbolInfo(account)     # Initialize SymbolInfo in the BacktestSimulator
    symbol_store.AddSymbol(test_symbol_info)   # Add symbol info to symbol store

    trade = sim.Trade(account)                  # Initialize Trade in the BacktestSimulator
    trade.SetExpertMagicNumber(12345)
    trade.SetDeviationInPoints(20)
    trade.SetTypeFillingBySymbol(test_symbol)

    # Load data from warmup_start_date to properly initialize indicators
    data = client.get_bars(
        symbol=test_symbol,
        timeframe=timeframe,
        date_from=warmup_start_date,
        date_to=end_date
    )

    data_m1 = client.get_bars(
        symbol=test_symbol,
        timeframe="M1",
        date_from=warmup_start_date,
        date_to=end_date
    )

    strategy = TrendFollowingStrategy(
            params={
                'symbol': test_symbol,
                'fast_period': 20,
                'slow_period': 50,
                'filter_period': 200
            }
        )
    strategy.on_init()  # Initialize strategy
    data = strategy.on_bar(data)  # Calculate signals

    run_config = {
        "signal_data": data,
        "execution_data": data_m1,
        "loop_model": "m1_ohlc",      # ohlc | m1_ohlc | synthetic_ticks | real_ticks
        "symbol": test_symbol,     # Used to fetch point from BacktestState symbol store
        "volume_lots": 0.1,        # Volume in lots
        "start_date": start_date,  # Trading starts here (after warmup)
        "end_date": end_date,      # Trading ends here
        "spread_mode": "data",     # "data" (default) OR "fixed" OR "variable"
        "spread_points": 10,       # Spread in points (only used when spread_mode="fixed")
        "spread_min": 5,           # Minimum spread in points (only used when spread_mode="variable")
        "spread_max": 20,          # Maximum spread in points (only used when spread_mode="variable")
        "verbose": False,           # Print verbose output
    }

    sim_start = time.time()
    simulator.run(run_config)
    sim_end = time.time()
    print(f"Simulation run() time: {sim_end - sim_start:.2f} seconds")



if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Backtest completed in {end_time - start_time:.2f} seconds")
