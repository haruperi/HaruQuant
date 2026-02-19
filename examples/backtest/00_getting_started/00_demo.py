"""
Basic Demonstration of using the C++ backtest engine

Usage:
    python tests/usage/backtest/00_getting_started/00_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add repo root to path for local imports
# Add repo root to path for local imports
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

BRIDGE_BUILD_DIR = PROJECT_ROOT / "build" / "bridge" / "Release"

# Prefer the local dev build of the C++ extension.
if str(BRIDGE_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_BUILD_DIR))

# Ensure dependent DLLs (fmt/spdlog) are discoverable on Windows.
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(BRIDGE_BUILD_DIR))

from apps.mt5 import MT5Client, get_mt5_api
mt5 = get_mt5_api()

from apps.simulation.data import AccountInfoSimulator
from apps.utils.logger import logger
from apps.sqlite.users import UserManager


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main() -> None:
    import hqt_engine.sim as sim

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for options 1 and 3)
    client = MT5Client()
    
    if not client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    try:
        print(f"Connected successfully!")
        print(f"Connection state: {client.connection_state.value}")
        print()

        account = sim.AccountInfo(10_000.0, "USD", 100)
        account.login = 12345678
        account.name = "Simulated Trader"
        account.server = "Sim-Server"
        account.company = "Simulated Company"

        simulator = sim.TradeSimulator(account)
        snapshot = simulator.account_info()

        print("TradeSimulator initialized")
        print(f"Server:         {account.Server()}")
        print(f"Company:        {account.Company()}")
        print(f"Currency:       {account.Currency()}")
        print(f"Leverage:       1:{account.Leverage()}")
        print(f"Balance:        {account.Balance()}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Shutdown MT5 connection
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")

if __name__ == "__main__":
    main()
