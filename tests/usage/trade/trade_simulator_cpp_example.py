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
import argparse

# Select the C++ backend BEFORE any simulation imports.
os.environ["SIM_ENGINE"] = "cpp"

from datetime import datetime
import time

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from apps.simulation.backend import get_backend, is_cpp_available
from apps.utils.logger import logger
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


def _import_cpp_bridge():
    """Import the C++ bridge and return (module, sim_submodule)."""
    import hqt_engine
    import hqt_engine.sim as csim

    return hqt_engine, csim


def _run_cpp_smoke() -> None:
    """Run a minimal in-process C++ smoke test without MT5 dependency."""
    hqt_engine, csim = _import_cpp_bridge()

    # Ensure the new bridge surface exists and basic logging can be wired.
    for required in ("set_log_level", "set_stderr_logging", "set_log_callback"):
        if not hasattr(hqt_engine, required):
            print(f"ERROR: hqt_engine missing required API: {required}")
            return

    def on_cpp_log(level: str, message: str) -> None:
        logger.info(f"[C++ smoke:{level}] {message}")

    hqt_engine.set_stderr_logging(False)
    hqt_engine.set_log_level("info")
    hqt_engine.set_log_callback(on_cpp_log)

    client = csim.SimulatorClient()
    symbol = csim.SymbolInfoData()
    symbol.symbol = "EURUSD"
    symbol.point = 0.00001
    symbol.spread = 10
    symbol.bid = 1.10000
    symbol.ask = 1.10010
    client.set_symbol_info(symbol)

    tick = csim.SymbolTickData()
    tick.time = 1
    tick.time_msc = 1000
    tick.bid = 1.10000
    tick.ask = 1.10010
    tick.last = 1.10000
    client.set_symbol_tick("EURUSD", tick)

    engine = csim.BacktestEngine(client)

    bars = []
    b1 = csim.BacktestBarStep()
    b1.time_msc = 60_000
    b1.close = 1.10000
    b1.entry_signal = 1
    bars.append(b1)

    b2 = csim.BacktestBarStep()
    b2.time_msc = 120_000
    b2.close = 1.10020
    b2.exit_signal = 1
    bars.append(b2)

    engine.run_trading_timeframe("EURUSD", 0.01, bars)

    print("C++ smoke run complete")
    print(f"Processed events : {engine.state().processed_events}")
    print(f"Completed trades : {len(engine.completed_trades())}")

    hqt_engine.set_log_callback(None)


def main(smoke: bool = False):
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

    if smoke:
        _run_cpp_smoke()
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
    parser = argparse.ArgumentParser(description="Trade simulator C++ example")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run minimal C++ bridge smoke test without MT5 dependency.",
    )
    args = parser.parse_args()
    main(smoke=args.smoke)

