"""Example usage of MT5 account info with optional core bridge init."""

import os
import sys

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (haruquant shim on top of haruquant.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if os.path.exists(BRIDGE_BUILD_DIR):
    if BRIDGE_BUILD_DIR not in sys.path:
        sys.path.insert(0, BRIDGE_BUILD_DIR)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
from apps.utils.logger import logger
import haruquant.core as sim


def main():
    print("=" * 60)
    print("AccountInfo Example")
    print("=" * 60)
    print()

    try:

        backend = "tester"  # set to: "mt5" or "tester"

        # Derived globals
        mt5 = get_mt5_api()
        client = MT5Utils.get_connected_client()
        mt5_account = client.account_info()
        account = sim.AccountInfo(mt5_account)  # Get default account info details from MT5

        if backend == "tester":
            # Override selected MT5-derived fields for tester backend.
            account.SetLogin(123456)
            account.SetServer("Backtest Simulation Server")
            account.SetCompany("HaruQuant")
            account.SetBalance(10000.0)
            account.SetCredit(0.0)
            account.SetProfit(0.0)
            account.SetEquity(10000.0)
            account.SetMargin(0.0)
            account.SetMarginFree(10000.0)
            account.SetMarginLevel(100.0)

        simulator = sim.BacktestSimulator(account)  # Initialize BacktestSimulator (core path)

        # Display account information
        print("ACCOUNT INFORMATION")
        print("-" * 60)
        print(f"Login:          {account.Login()}")
        print(f"Name:           {account.Name()}")
        print(f"Server:         {account.Server()}")
        print(f"Company:        {account.Company()}")
        print(f"Currency:       {account.Currency()}")
        print(f"Leverage:       1:{account.Leverage()}")
        print()

        # Display account mode
        print("ACCOUNT MODE")
        print("-" * 60)
        print(f"Trade Mode:     {account.TradeMode()}")
        print(f"Margin Mode:    {account.MarginMode()}")
        print()

        # Display account permissions
        print("PERMISSIONS")
        print("-" * 60)
        print(f"Trade Allowed:  {'Yes' if account.TradeAllowed() else 'No'}")
        print(f"Expert Allowed: {'Yes' if account.TradeExpert() else 'No'}")
        print(f"Limit Orders:   {account.LimitOrders()} (0 = unlimited)")
        print()

        # Display account balance and equity
        print("BALANCE & EQUITY")
        print("-" * 60)
        print(f"Balance:        {account.Balance():.2f} {account.Currency()}")
        print(f"Credit:         {account.Credit():.2f} {account.Currency()}")
        print(f"Profit:         {account.Profit():.2f} {account.Currency()}")
        print(f"Equity:         {account.Equity():.2f} {account.Currency()}")
        print()

        # Display margin information
        print("MARGIN INFORMATION")
        print("-" * 60)
        print(f"Margin Used:    {account.Margin():.2f} {account.Currency()}")
        print(f"Free Margin:    {account.MarginFree():.2f} {account.Currency()}")
        if account.Margin() > 0:
            print(f"Margin Level:   {account.MarginLevel():.2f}%")
        else:
            print("Margin Level:   N/A (no open positions)")
        print(f"Margin Call:    {account.MarginCall()}")
        print(f"Margin Stopout: {account.MarginStopOut()}")
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
