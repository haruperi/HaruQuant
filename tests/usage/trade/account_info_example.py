"""
Example usage of AccountInfo with different providers.

This example demonstrates:
- Connecting to MT5 using stored credentials
- Reading account properties with AccountInfo
- Running margin/profit helper calculations

This example demonstrates two ways to use AccountInfo:
1. AccountInfo() - Live trading with MT5 connection (default)
2. AccountInfo(simulator) - Simulator trading with MT5 settings + custom settings
"""



import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client, get_mt5_api
mt5 = get_mt5_api()

from apps.trade import AccountInfo
from apps.simulation.data import TradeSimulator, AccountInfoSimulator
from apps.utils.logger import logger
from apps.sqlite.users import UserManager


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 60)
    print("AccountInfo Example")
    print("=" * 60)
    print()

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

        # CHOOSE PROVIDER (uncomment one option)
        
        # Option 1: Live Trading with MT5 AccountInfo instance
        account = AccountInfo()

        # Option 2: Simulator with Custom Settings
        # simulator_account_data = AccountInfoSimulator(
        #     #balance=50000,
        # )
        # simulator = TradeSimulator(simulator_account_data)
        # account = AccountInfo(api=simulator)
  



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
        print(f"Trade Mode:     {account.TradeModeDescription()}")
        print(f"Margin Mode:    {account.MarginModeDescription()}")
        print(f"Stopout Mode:   {account.StopoutModeDescription()}")
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
        print(f"Free Margin:    {account.FreeMargin():.2f} {account.Currency()}")
        if account.Margin() > 0:
            print(f"Margin Level:   {account.MarginLevel():.2f}%")
        else:
            print(f"Margin Level:   N/A (no open positions)")
        print(f"Margin Call:    {account.MarginCall():.2f}")
        print(f"Margin Stopout: {account.StopoutMode():.2f}")
        print()

        # Calculate some metrics
        if account.Balance() > 0:
            profit_percent = (account.Profit() / account.Balance()) * 100
            print("PERFORMANCE METRICS")
            print("-" * 60)
            print(f"P/L Percentage: {profit_percent:+.2f}%")
            if account.Margin() > 0 and account.Equity() > 0:
                leverage_used = (account.Margin() / account.Equity()) * 100
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
            req_margin = account.MarginCheck(symbol, mt5.ORDER_TYPE_BUY, volume, 1.1000)  # type: ignore
            if req_margin is not None:
                print(
                    f"Margin for {volume} lots {symbol} BUY at 1.1000: {req_margin:.2f} {account.Currency()}"
                )
            else:
                print(f"Margin check failed for {symbol}")
        except Exception as e:
            print(f"Margin check error: {e}")

        # 2. Profit Check
        try:
            est_profit = account.OrderProfitCheck(
                symbol, mt5.ORDER_TYPE_BUY, volume, 1.1000, 1.1050   # type: ignore
            )  
            if est_profit is not None:
                print(
                    f"Est. Profit for {volume} lots {symbol} BUY (1.1000 -> 1.1050): {est_profit:.2f} {account.Currency()}"
                )
            else:
                print(f"Profit check failed for {symbol}")
        except Exception as e:
            print(f"Profit check error: {e}")

        # 3. Free Margin Check
        try:
            has_margin = account.FreeMarginCheck(
                symbol, mt5.ORDER_TYPE_BUY, volume, 1.1000   # type: ignore
            )
            print(
                f"Sufficient free margin for {volume} lots {symbol} BUY: {'Yes' if has_margin else 'No'}"
            )
        except Exception as e:
            print(f"Free margin check error: {e}")

        # 4. Max Lot Check
        try:
            max_lot = account.MaxLotCheck(symbol, mt5.ORDER_TYPE_BUY, 1.1000, 100)  # type: ignore
            print(f"Max lots for {symbol} BUY at 1.1000 (100% equity): {max_lot}")
        except Exception as e:
            print(f"Max lot check error: {e}")

        # Display underlying enum values
        print()
        print("ACCOUNT SETTINGS (RAW ENUMS)")
        print("-" * 60)
        print(f"Trade Mode:     {account.TradeMode()}")
        print(f"Margin Mode:    {account.MarginMode()}")
        print(f"Stopout Mode:   {account.StopoutMode()}")
        print()

        # Display summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Account {account.Login()} ({account.TradeModeDescription()})")
        print(f"Balance: {account.Balance():.2f} {account.Currency()}")
        print(f"Equity: {account.Equity():.2f} {account.Currency()}")
        print(f"Free Margin: {account.FreeMargin():.2f} {account.Currency()}")

        if account.Profit() != 0:
            profit_sign = "+" if account.Profit() > 0 else ""
            print(
                f"Current P/L: {profit_sign}{account.Profit():.2f} {account.Currency()}"
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


