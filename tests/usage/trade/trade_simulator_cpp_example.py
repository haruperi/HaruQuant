"""
Example usage of TradeSimulator with the C++ backend.

This example mirrors trade_simulator_example.py but routes through the
C++ BacktestEngine by setting ``SIM_ENGINE=cpp`` before the simulation runs.

Requires:
- The ``hqt_engine`` C++ extension to be installed.
- MT5 terminal running with valid credentials in the database.
- data_modelling is hardcoded to "trading_timeframe" (only mode C++ supports).
"""

import sys
import os

# Select the C++ backend BEFORE any simulation imports.
os.environ["SIM_ENGINE"] = "cpp"

from datetime import datetime
import time

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from apps.simulation.backend import get_backend, is_cpp_available
from apps.logger import logger
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from data.strategies.trend_following import TrendFollowingStrategy

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
    print("Trade Simulator Example  [C++ Backend]")
    print("=" * 70)
    print()

    # Confirm backend selection
    backend = get_backend()
    cpp_available = is_cpp_available()
    print(f"Backend requested : {backend.value}")
    print(f"C++ extension     : {'available' if cpp_available else 'NOT FOUND'}")
    print()

    if not cpp_available:
        print("ERROR: hqt_engine.sim is not installed. Build the C++ extension first.")
        return

    # Get credentials and connect to MT5
    creds = get_mt5_credentials()
    client = MT5Client()

    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    # Global variables
    magic_number = 12345
    slippage = 0
    commission_per_contract = 7
    eurusd = "EURUSD"
    volume = 0.1

    # Date configuration
    warmup_start_date = datetime(2024, 1, 1)  # Data download starts here
    start_date = datetime(2025, 1, 1)          # Trading starts here
    end_date = datetime(2025, 12, 31)          # Trading ends here

    data_modelling = "trading_timeframe"        # Only mode C++ supports
    engine_type = "event_driven"

    # Initialize AccountInfoSimulator
    account_info = AccountInfoSimulator()

    # Initialize Symbols
    eurusd_info = SymbolInfoSimulator.from_mt5_symbol(eurusd)

    # Initialize TradeSimulator
    simulator = TradeSimulator(
        simulator_name="EURUSD_Backtest_CPP",
        mt5_client=client,
        account_info=account_info,
        symbols={eurusd: eurusd_info},
    )

    # Trading timeframe data (signals are generated from this)
    data = client.get_bars(symbol=eurusd, timeframe="H1", date_from=warmup_start_date, date_to=end_date)
    if data is None or len(data) == 0:
        print("No H1 data available.")
        client.shutdown()
        return

    # Initialize strategy
    simulator.trade.SetExpertMagicNumber(magic_number)
    simulator.trade.SetDeviationInPoints(slippage)
    strategy = TrendFollowingStrategy(
        params={
            "symbol": eurusd,
            "fast_period": 20,
            "slow_period": 50,
            "filter_period": 200,
        }
    )

    strategy.on_init()

    # Calculate indicators and signals
    data = strategy.on_bar(data)

    # Run simulation
    backtest_metadata = {
        "strategy_name": "TrendFollowingStrategy",
        "strategy_version": "1.0.0",
        "start_date": start_date,
        "end_date": end_date,
        "engine_type": "simulator",
        "data_resolution": "H1",
        "config_hash": "trend_following_eurusd_h1",
        "data_modelling": data_modelling,
        "symbols": [eurusd],
        "timeframes": ["H1"],
        "initial_balance": account_info.balance,
        "alias": "EURUSD H1 Trend Following (C++)",
        "description": "Simulator run via C++ BacktestEngine",
    }

    print(f"Running simulation via C++ backend...")
    start_time = time.time()

    simulator.run(
        data=data,
        strategy=strategy,
        symbol=eurusd,
        volume=volume,
        verbose=True,
        save_db=False,
        metadata=backtest_metadata,
        step_data=None,
        data_modelling=data_modelling,
        engine_type=engine_type,
        commission_per_contract=commission_per_contract,
        slippage_points=slippage,
        start_date=start_date,
        end_date=end_date,
    )

    end_time = time.time()
    elapsed = end_time - start_time

    # Print summary
    print()
    print("-" * 70)
    print(f"Backend           : C++ (BacktestEngine)")
    print(f"Completed trades  : {len(simulator._completed_trades)}")
    print(f"Elapsed time      : {elapsed:.2f} seconds")
    print("-" * 70)

    # Disconnect MT5
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
