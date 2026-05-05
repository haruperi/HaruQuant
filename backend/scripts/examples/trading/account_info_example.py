"""Example usage of MT5 account info with optional core bridge init."""

import os
import sys

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.simulation.engine import Engine


def main():
    print("=" * 60)
    print("AccountInfo Example")
    print("=" * 60)
    print()

    try:

        backend = "sim"  # set to: "mt5" or "sim"
        engine_instance = Engine(backend=backend)
        api = engine_instance.api
        account = api.account_info()

        if backend == "sim":
            # Override selected MT5-derived fields for tester backend.
            account['login'] = 123456
            account['server'] = "Backtest Simulation Server"
            account['company'] = "HaruQuant"
            account['balance'] = 10000.0
            account['credit'] = 0.0
            account['profit'] = 0.0
            account['equity'] = 10000.0
            account['margin'] = 0.0
            account['margin_free'] = 10000.0
            account['margin_level'] = 100.0

        # Display account information
        print(f"ACCOUNT INFORMATION - {backend}")
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
        if getattr(account, 'margin', 0.0) > 0:
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
        if 'engine_instance' in locals():
            print("\nShutting down MT5 connection...")
            engine_instance.client.shutdown()
            print("Disconnected.")


if __name__ == "__main__":
    main()
