"""
Example usage of SymbolInfo with different providers.

This example demonstrates two ways to use SymbolInfo:
1. MT5SymbolProvider - Live trading with MT5 connection
2. BacktestSymbolProvider - Backtest with cached MT5 symbol data

Simply uncomment the provider you want to use.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import SymbolInfo, MT5SymbolProvider, BacktestSymbolProvider
from datetime import datetime


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


def normalize_price(price: float, tick_size: float, digits: int) -> float:
    """Normalize price to tick size and digits."""
    if tick_size != 0:
        return round(round(price / tick_size) * tick_size, digits)
    return round(price, digits)


def main():
    print("=" * 60)
    print("SymbolInfo Example")
    print("=" * 60)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for both options)
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

        # Test with different symbols
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        for symbol_name in symbols:
            print(f"\n{symbol_name}")
            print("=" * 60)

            # Option 1: Live Trading with MT5
            provider = MT5SymbolProvider(client, symbol_name)
            print("Using: MT5SymbolProvider (Live Trading)")

            # Option 2: Backtesting with Cached MT5 Symbol Data
            # # Fetches symbol specs from MT5 once, then allows tick updates
            # provider = BacktestSymbolProvider(client, symbol_name)
            # # Update tick for backtesting
            # provider.set_tick(bid=1.1000, ask=1.1002, time=datetime.now())
            # print("Using: BacktestSymbolProvider (Cached MT5 Data)")

            symbol = SymbolInfo(provider)

            # Display basic information
            print("\nBASIC INFORMATION")
            print("-" * 60)
            print(f"Symbol:         {symbol.name()}")
            print(f"Description:    {symbol.description()}")
            print(f"Path:           {symbol.path()}")
            print(f"Digits:         {symbol.digits()}")
            print(f"Point:          {symbol.point()}")
            print(f"Tick Size:      {symbol.tick_size()}")

            # Display current prices
            print("\nCURRENT PRICES")
            print("-" * 60)
            print(f"Bid:            {symbol.bid():.{symbol.digits()}f}")
            print(f"Ask:            {symbol.ask():.{symbol.digits()}f}")
            print(f"Last:           {symbol.last():.{symbol.digits()}f}")
            print(f"Spread:         {symbol.spread()} points")
            print(f"Spread Float:   {'Yes' if symbol.spread_float() else 'No'}")
            print(f"Time:           {symbol.time()}")

            # Display daily high/low
            print("\nDAILY HIGH/LOW")
            print("-" * 60)
            print(f"Bid High:       {symbol.bid_high():.{symbol.digits()}f}")
            print(f"Bid Low:        {symbol.bid_low():.{symbol.digits()}f}")
            print(f"Ask High:       {symbol.ask_high():.{symbol.digits()}f}")
            print(f"Ask Low:        {symbol.ask_low():.{symbol.digits()}f}")

            # Display trading information
            print("\nTRADING INFORMATION")
            print("-" * 60)
            print(f"Trade Mode:     {symbol.trade_mode_description()}")
            print(f"Execution:      {symbol.trade_execution_description()}")
            print(f"Calc Mode:      {symbol.trade_calc_mode_description()}")
            print(f"Stops Level:    {symbol.stops_level()} points")
            print(f"Freeze Level:   {symbol.freeze_level()} points")

            # Display lot parameters
            print("\nLOT PARAMETERS")
            print("-" * 60)
            print(f"Contract Size:  {symbol.contract_size():.2f}")
            print(f"Min Lot:        {symbol.lots_min():.2f}")
            print(f"Max Lot:        {symbol.lots_max():.2f}")
            print(f"Lot Step:       {symbol.lots_step():.2f}")
            print(f"Lot Limit:      {symbol.lots_limit():.2f}")

            # Display swap information
            print("\nSWAP INFORMATION")
            print("-" * 60)
            print(f"Swap Mode:      {symbol.swap_mode_description()}")
            print(f"Swap Long:      {symbol.swap_long():.2f}")
            print(f"Swap Short:     {symbol.swap_short():.2f}")
            # Note: DayOfWeek string representation comes from Enum, we might use name.title()
            print(f"Triple Swap:    {symbol.swap_rollover3days().name.title()}")

            # Display currency information
            print("\nCURRENCY INFORMATION")
            print("-" * 60)
            print(f"Base Currency:  {symbol.currency_base()}")
            print(f"Profit Currency:{symbol.currency_profit()}")
            print(f"Margin Currency:{symbol.currency_margin()}")

            # Display margin information
            print("\nMARGIN INFORMATION")
            print("-" * 60)
            print(f"Margin Initial: {symbol.margin_initial():.2f}")
            print(f"Margin Maint.:  {symbol.margin_maintenance():.2f}")
            print(f"Margin Hedged:  {symbol.margin_hedged():.2f}")

            # Display session information (if available)
            print("\nSESSION INFORMATION")
            print("-" * 60)
            # SymbolInfo exposes session methods directly
            deals = symbol.session_deals()
            if deals > 0:
                print(f"Deals:          {deals}")
                print(f"Buy Orders:     {symbol.session_buy_orders()}")
                print(f"Sell Orders:    {symbol.session_sell_orders()}")
                print(f"Turnover:       {symbol.session_turnover():.2f}")
                print(f"Session Open:   {symbol.session_open():.{symbol.digits()}f}")
                print(f"Session Close:  {symbol.session_close():.{symbol.digits()}f}")
            else:
                print("Session data not available")

        # Test normalize_price function
        print("\n" + "=" * 60)
        print("PRICE NORMALIZATION TEST")
        print("=" * 60)

        # Use EURUSD for this test
        provider = MT5SymbolProvider(client, "EURUSD")
        symbol = SymbolInfo(provider)

        test_prices = [1.105678, 1.105634, 1.105699]
        print(f"\nSymbol: {symbol.name()}")
        print(f"Digits: {symbol.digits()}")
        print(f"Tick Size: {symbol.tick_size()}")
        print()

        for price in test_prices:
            # Use SymbolInfo's normalize_price method
            normalized = symbol.normalize_price(price)
            print(
                f"Original: {price:.6f} -> Normalized: {normalized:.{symbol.digits()}f}"
            )

            # Additional Properties and Methods Test
            print("\n" + "=" * 60)
            print("ADDITIONAL COVERAGE TEST")
            print("=" * 60)

            print(f"Volume: {symbol.volume()}")
            print(f"Volume High: {symbol.volume_high()}")
            print(f"Volume Low: {symbol.volume_low()}")

            print(f"Is Synchronized: {symbol.is_synchronized()}")
            print(f"Selected: {symbol.select()}")

            # Test Refresh methods
            print(f"Refresh Symbol: {symbol.refresh()}")
            print(f"Refresh Rates: {symbol.refresh_rates()}")

            # Test Tick Values
            print(f"Tick Value: {symbol.tick_value()}")
            print(f"Tick Profit: {symbol.tick_value_profit()}")
            print(f"Tick Loss: {symbol.tick_value_loss()}")

            # Test direct info access
        test_prices = [1.105678, 1.105634, 1.105699]
        print(f"\nSymbol: {symbol.name()}")
        print(f"Digits: {symbol.digits()}")
        print(f"Tick Size: {symbol.tick_size()}")
        print()

        for price in test_prices:
            # Use SymbolInfo's normalize_price method
            normalized = symbol.normalize_price(price)
            print(
                f"Original: {price:.6f} -> Normalized: {normalized:.{symbol.digits()}f}"
            )

        # Additional Properties and Methods Test
        print("\n" + "=" * 60)
        print("ADDITIONAL COVERAGE TEST")
        print("=" * 60)

        print(f"Volume: {symbol.volume()}")
        print(f"Volume High: {symbol.volume_high()}")
        print(f"Volume Low: {symbol.volume_low()}")

        print(f"Is Synchronized: {symbol.is_synchronized()}")
        print(f"Selected: {symbol.select()}")

        # Test Refresh methods
        print(f"Refresh Symbol: {symbol.refresh()}")
        print(f"Refresh Rates: {symbol.refresh_rates()}")

        # Test Tick Values
        print(f"Tick Value: {symbol.tick_value()}")
        print(f"Tick Profit: {symbol.tick_value_profit()}")
        print(f"Margin Initial: {symbol.margin_initial()}")
        print(f"Margin Maintenance: {symbol.margin_maintenance()}")
        print(f"Margin Long: {symbol.margin_long()}")
        print(f"Margin Short: {symbol.margin_short()}")
        print(f"Margin Limit: {symbol.margin_limit()}")
        print(f"Margin Stop: {symbol.margin_stop()}")
        print(f"Margin Stop Limit: {symbol.margin_stop_limit()}")

        # Test direct info access
        print(f"Info Double (Bid): {symbol.info_double('bid')}")
        print(f"Info Integer (Digits): {symbol.info_integer('digits')}")
        print(f"Info String (Name): {symbol.info_string('name')}")

        # Test Market Watch check
        print(f"Check Market Watch: {symbol.check_market_watch()}")

        print("\n" + "=" * 70)
        print("Example completed successfully!")
        print("=" * 70)

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
