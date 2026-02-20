"""
Example usage of AccountInfo with different providers.

This example demonstrates:
- Connecting to MT5 using stored credentials
- Reading account properties with AccountInfo
- Running margin/profit helper calculations

This example demonstrates two ways to use AccountInfo:
1. AccountInfo() - Live trading with MT5 connection (default)
2. C++ TradeSimulator backend seeded from MT5 data
"""

import os
import sys

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (hqt_engine.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if os.path.exists(BRIDGE_BUILD_DIR):
    if BRIDGE_BUILD_DIR not in sys.path:
        sys.path.insert(0, BRIDGE_BUILD_DIR)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
from apps.utils.logger import logger
import hqt_engine.sim as csim

mt5 = get_mt5_api()

def main():
    backend = "tester"  # set to: "mt5" or "tester"

    print("=" * 60)
    print("AccountInfo Example")
    print("=" * 60)
    print()

    try:
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5.")
            return
        print("Connected successfully!")
        print(f"Connection state: {client.connection_state.value}")
        print()
        simulator = mt5
        account = simulator.account_info()

        if backend != "mt5":
            cpp_account = csim.AccountInfo(account)
            cpp_account.balance = 50000.0
            cpp_account.credit = 0.0
            cpp_account.profit = 0.0
            cpp_account.equity = 50000.0
            cpp_account.margin = 0.0
            cpp_account.margin_free = 50000.0
            cpp_account.margin_level = 100.0
            cpp_account.server = "Simulator Account"
            cpp_account.company = "HaruQuant"
            
            simulator = csim.TradeSimulator(cpp_account)
            account = simulator.account_info()
            print("Using tester backend.")
            print()

        # Display account information
        print("ACCOUNT INFORMATION")
        print("-" * 60)
        print(f"Login:          {account.login}")
        print(f"Name:           {account.name}")
        print(f"Server:         {account.server}")
        print(f"Company:        {account.company}")
        print(f"Currency:       {account.currency}")
        print(f"Leverage:       1:{account.leverage}")
        print()

        # Display account mode
        print("ACCOUNT MODE")
        print("-" * 60)
        print(f"Trade Mode:     {account.trade_mode}")
        print(f"Margin Mode:    {account.margin_mode}")
        print()

        # Display account permissions
        print("PERMISSIONS")
        print("-" * 60)
        print(f"Trade Allowed:  {'Yes' if account.trade_allowed else 'No'}")
        print(f"Expert Allowed: {'Yes' if account.trade_expert else 'No'}")
        print(f"Limit Orders:   {account.limit_orders} (0 = unlimited)")
        print()

        # Display account balance and equity
        print("BALANCE & EQUITY")
        print("-" * 60)
        print(f"Balance:        {account.balance:.2f} {account.currency}")
        print(f"Credit:         {account.credit:.2f} {account.currency}")
        print(f"Profit:         {account.profit:.2f} {account.currency}")
        print(f"Equity:         {account.equity:.2f} {account.currency}")
        print()

        # Display margin information
        print("MARGIN INFORMATION")
        print("-" * 60)
        print(f"Margin Used:    {account.margin:.2f} {account.currency}")
        print(f"Free Margin:    {account.margin_free:.2f} {account.currency}")
        if account.margin > 0:
            print(f"Margin Level:   {account.margin_level:.2f}%")
        else:
            print("Margin Level:   N/A (no open positions)")
        print(f"Margin Call:    {account.margin_so_call}")
        print(f"Margin Stopout: {account.margin_so_so}")
        print()

        print()
        print("=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if client is not None:
            print("\nShutting down MT5 connection...")
            client.shutdown()
            print("Disconnected.")


if __name__ == "__main__":
    main()
