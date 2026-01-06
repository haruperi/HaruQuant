"""
Example usage of AccountInfo with different providers.

This example demonstrates three ways to use AccountInfo:
1. MT5AccountProvider - Live trading with MT5 connection
2. BacktestAccountProvider - Custom backtest settings
3. BacktestAccountProvider.from_mt5_account() - Backtest matching MT5 settings

Simply uncomment the provider you want to use.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import (
    AccountInfo,
    MT5AccountProvider,
    BacktestAccountProvider,
    AccountMarginMode,
    OrderType,
)


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"  # Change this to your username
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        sys.exit(1)

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        sys.exit(1)

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")
    return creds


def main():
    print("=" * 60)
    print("AccountInfo Example")
    print("=" * 60)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for options 1 and 3)
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    print("Connecting to MT5...")
    if not client.is_connected():
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    try:
        print(f"Connected successfully!")
        print(f"Connection state: {client.connection_state.value}")
        print()

        # ============================================================
        # CHOOSE YOUR PROVIDER (uncomment one option)
        # ============================================================

        # Option 1: Live Trading with MT5
        # Uses MT5's native calculation functions (order_calc_margin, order_calc_profit)
        provider = MT5AccountProvider(client)
        print("Using: MT5AccountProvider (Live Trading)")

        # Option 2: Backtesting with Custom Settings
        # Simulates account without MT5 connection
        # provider = BacktestAccountProvider(
        #     initial_balance=10000.0,
        #     currency="USD",
        #     leverage=100,
        #     margin_mode=AccountMarginMode.RETAIL_HEDGING,
        # )
        # print("Using: BacktestAccountProvider (Custom Settings)")

        # Option 3: Backtesting Matching MT5 Account
        # Copies all settings from your MT5 account for realistic backtesting
        # provider = BacktestAccountProvider.from_mt5_account(
        #     client,
        #     initial_balance=10000,  # Optional: override balance
        #     symbols=["EURUSD", "GBPUSD", "XAUUSD"]  # Optional: symbols to fetch
        # )
        # print("Using: BacktestAccountProvider (Matching MT5)")

        print()

        # Create AccountInfo instance
        account = AccountInfo(provider)

        # Display account information
        print("ACCOUNT INFORMATION")
        print("-" * 60)
        print(f"Login:          {account.login()}")
        print(f"Name:           {account.name()}")
        print(f"Server:         {account.server()}")
        print(f"Company:        {account.company()}")
        print(f"Currency:       {account.currency()}")
        print(f"Leverage:       1:{account.leverage()}")
        print()

        # Display account mode
        print("ACCOUNT MODE")
        print("-" * 60)
        print(f"Trade Mode:     {account.trade_mode_description()}")
        print(f"Margin Mode:    {account.margin_mode_description()}")
        print(f"Stopout Mode:   {account.stopout_mode_description()}")
        print()

        # Display account permissions
        print("PERMISSIONS")
        print("-" * 60)
        print(f"Trade Allowed:  {'Yes' if account.trade_allowed() else 'No'}")
        print(f"Expert Allowed: {'Yes' if account.trade_expert() else 'No'}")
        print(f"Limit Orders:   {account.limit_orders()} (0 = unlimited)")
        print()

        # Display account balance and equity
        print("BALANCE & EQUITY")
        print("-" * 60)
        print(f"Balance:        {account.balance():.2f} {account.currency()}")
        print(f"Credit:         {account.credit():.2f} {account.currency()}")
        print(f"Profit:         {account.profit():.2f} {account.currency()}")
        print(f"Equity:         {account.equity():.2f} {account.currency()}")
        print()

        # Display margin information
        print("MARGIN INFORMATION")
        print("-" * 60)
        print(f"Margin Used:    {account.margin():.2f} {account.currency()}")
        print(f"Free Margin:    {account.free_margin():.2f} {account.currency()}")
        if account.margin() > 0:
            print(f"Margin Level:   {account.margin_level():.2f}%")
        else:
            print(f"Margin Level:   N/A (no open positions)")
        print(f"Margin Call:    {account.margin_call():.2f}")
        print(f"Margin Stopout: {account.margin_stopout():.2f}")
        print()

        # Calculate some metrics
        if account.balance() > 0:
            profit_percent = (account.profit() / account.balance()) * 100
            print("PERFORMANCE METRICS")
            print("-" * 60)
            print(f"P/L Percentage: {profit_percent:+.2f}%")
            if account.margin() > 0 and account.equity() > 0:
                leverage_used = (account.margin() / account.equity()) * 100
                print(f"Leverage Used:  {leverage_used:.2f}%")
            print()

        # Demonstrate trading checks
        print("TRADING CHECKS")
        print("-" * 60)

        # Test symbol for checks
        symbol = "EURUSD"
        volume = 1.0

        # 1. Margin Check
        try:
            req_margin = account.margin_check(symbol, OrderType.BUY, volume, 1.1000)  # type: ignore
            if req_margin is not None:
                print(
                    f"Margin for {volume} lots {symbol} BUY at 1.1000: {req_margin:.2f} {account.currency()}"
                )
            else:
                print(f"Margin check failed for {symbol}")
        except Exception as e:
            print(f"Margin check error: {e}")

        # 2. Profit Check
        try:
            est_profit = account.order_profit_check(
                symbol, OrderType.BUY, volume, 1.1000, 1.1050   # type: ignore
            )  
            if est_profit is not None:
                print(
                    f"Est. Profit for {volume} lots {symbol} BUY (1.1000 -> 1.1050): {est_profit:.2f} {account.currency()}"
                )
            else:
                print(f"Profit check failed for {symbol}")
        except Exception as e:
            print(f"Profit check error: {e}")

        # 3. Free Margin Check
        try:
            has_margin = account.free_margin_check(
                symbol, OrderType.BUY, volume, 1.1000   # type: ignore
            )
            print(
                f"Sufficient free margin for {volume} lots {symbol} BUY: {'Yes' if has_margin else 'No'}"
            )
        except Exception as e:
            print(f"Free margin check error: {e}")

        # 4. Max Lot Check
        try:
            max_lot = account.max_lot_check(symbol, OrderType.BUY, 1.1000, 100)  # type: ignore
            print(f"Max lots for {symbol} BUY at 1.1000 (100% equity): {max_lot}")
        except Exception as e:
            print(f"Max lot check error: {e}")

        # Display underlying enum values
        print()
        print("ACCOUNT SETTINGS (RAW ENUMS)")
        print("-" * 60)
        print(f"Trade Mode:     {account.trade_mode()}")
        print(f"Margin Mode:    {account.margin_mode()}")
        print(f"Stopout Mode:   {account.stopout_mode()}")
        print()

        # Display summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Account {account.login()} ({account.trade_mode_description()})")
        print(f"Balance: {account.balance():.2f} {account.currency()}")
        print(f"Equity: {account.equity():.2f} {account.currency()}")
        print(f"Free Margin: {account.free_margin():.2f} {account.currency()}")

        if account.profit() != 0:
            profit_sign = "+" if account.profit() > 0 else ""
            print(
                f"Current P/L: {profit_sign}{account.profit():.2f} {account.currency()}"
            )

        print()
        print("=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

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
