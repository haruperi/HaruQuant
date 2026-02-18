"""
Example usage of SymbolInfo with different providers.

This example demonstrates two ways to use SymbolInfo:
1. SymbolInfo(symbol, api=client) - Live trading with MT5 connection
2. SymbolInfo(symbol, api=simulator) - Simulation with custom settings

Simply uncomment the option you want to use.
"""

import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from apps.trade import SymbolInfo
from apps.simulation.data import TradeSimulator, SymbolInfoSimulator, SymbolTickSimulator


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
    print("SymbolInfo Example")
    print("=" * 60)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1 and to fetch real data for Option 2 defaults)
    client = MT5Client()
    
    if not client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print(f"Connected successfully!")
    print(f"Connection state: {client.connection_state.value}")
    print()

    # ============================================================
    # CHOOSE YOUR OPTION
    # ============================================================

    # Test with different symbols
    symbols = ["EURUSD", "GBPUSD"]

    for symbol_name in symbols:
        print(f"\nProcessing {symbol_name}...")
        print("=" * 60)

        # Option 1: Live Trading with MT5 (Default)
        # symbol = SymbolInfo(symbol_name)
        # print("Using: MT5 Live Connection")

        # Option 2: Simulator with Custom Settings (Uncomment to use)
        sim_info = SymbolInfoSimulator.from_mt5_symbol(symbol_name)
        # Override some values if needed
        sim_info.spread = 5
        sim_tick = SymbolTickSimulator(bid=1.2345, ask=1.2350, last=1.2348)
        simulator = TradeSimulator(
            symbols_data={symbol_name: sim_info},
            ticks_data={symbol_name: sim_tick}
        )
        symbol = SymbolInfo(symbol_name, api=simulator)
        print("Using: Simulator (Custom Data)")

        if hasattr(symbol._api, "symbol_select"):
            symbol.Select(True)
        symbol.Refresh()
        symbol.RefreshRates()

        if not symbol.Select():
            print(f"Failed to select symbol {symbol_name}")
            continue

        # Display basic information
        print("\nBASIC INFORMATION")
        print("-" * 60)
        print(f"Symbol:         {symbol.Name()}")
        print(f"Description:    {symbol.Description()}")
        print(f"Path:           {symbol.Path()}")
        print(f"Digits:         {symbol.Digits()}")
        print(f"Point:          {symbol.Point()}")
        print(f"Tick Size:      {symbol.TickSize()}")

        # Display current prices
        print("\nCURRENT PRICES")
        print("-" * 60)
        digits = symbol.Digits()
        print(f"Bid:            {symbol.Bid():.{digits}f}")
        print(f"Ask:            {symbol.Ask():.{digits}f}")
        print(f"Last:           {symbol.Last():.{digits}f}")
        print(f"Spread:         {symbol.Spread()} points")
        print(f"Spread Float:   {'Yes' if symbol.SpreadFloat() else 'No'}")
        print(f"Time:           {symbol.Time()}")

        # Display daily high/low
        print("\nDAILY HIGH/LOW")
        print("-" * 60)
        print(f"Bid High:       {symbol.BidHigh():.{digits}f}")
        print(f"Bid Low:        {symbol.BidLow():.{digits}f}")
        print(f"Ask High:       {symbol.AskHigh():.{digits}f}")
        print(f"Ask Low:        {symbol.AskLow():.{digits}f}")

        # Display trading information
        print("\nTRADING INFORMATION")
        print("-" * 60)
        print(f"Trade Mode:     {symbol.TradeModeDescription()}")
        print(f"Execution:      {symbol.TradeExecutionDescription()}")
        print(f"Calc Mode:      {symbol.TradeCalcModeDescription()}")
        print(f"Stops Level:    {symbol.StopsLevel()} points")
        print(f"Freeze Level:   {symbol.FreezeLevel()} points")

        # Display lot parameters
        print("\nLOT PARAMETERS")
        print("-" * 60)
        print(f"Contract Size:  {symbol.ContractSize():.2f}")
        print(f"Min Lot:        {symbol.LotsMin():.2f}")
        print(f"Max Lot:        {symbol.LotsMax():.2f}")
        print(f"Lot Step:       {symbol.LotsStep():.2f}")
        print(f"Lot Limit:      {symbol.LotsLimit():.2f}")

        # Display swap information
        print("\nSWAP INFORMATION")
        print("-" * 60)
        print(f"Swap Mode:      {symbol.SwapModeDescription()}")
        print(f"Swap Long:      {symbol.SwapLong():.2f}")
        print(f"Swap Short:     {symbol.SwapShort():.2f}")
        print(f"Triple Swap:    {symbol.SwapRollover3DaysDescription()}")

        # Display currency information
        print("\nCURRENCY INFORMATION")
        print("-" * 60)
        print(f"Base Currency:  {symbol.CurrencyBase()}")
        print(f"Profit Currency:{symbol.CurrencyProfit()}")
        print(f"Margin Currency:{symbol.CurrencyMargin()}")

        # Display margin information
        print("\nMARGIN INFORMATION")
        print("-" * 60)
        print(f"Margin Initial: {symbol.MarginInitial():.2f}")
        print(f"Margin Maint.:  {symbol.MarginMaintenance():.2f}")
        # Display session information (if available)
        print("\nSESSION INFORMATION")
        print("-" * 60)
        # SymbolInfo exposes session methods directly
        deals = symbol.SessionDeals()
        if deals > 0:
            print(f"Deals:          {deals}")
            print(f"Buy Orders:     {symbol.SessionBuyOrders()}")
            print(f"Sell Orders:    {symbol.SessionSellOrders()}")
            print(f"Turnover:       {symbol.SessionTurnover():.2f}")
            print(f"Session Open:   {symbol.SessionOpen():.{digits}f}")
            print(f"Session Close:  {symbol.SessionClose():.{digits}f}")
        else:
            print("Session data not available")

        # Test normalize_price function
        print("\n" + "=" * 60)
        print("PRICE NORMALIZATION TEST")
        print("=" * 60)

        test_prices = [1.105678, 1.105634, 1.105699]
        print(f"\nSymbol: {symbol.Name()}")
        print(f"Digits: {symbol.Digits()}")
        print(f"Tick Size: {symbol.TickSize()}")
        print()

        for price in test_prices:
            # Use SymbolInfo's normalize_price method
            normalized = symbol.NormalizePrice(price)
            print(
                f"Original: {price:.6f} -> Normalized: {normalized:.{symbol.Digits()}f}"
            )

        # Additional Properties and Methods Test
        print("\n" + "=" * 60)
        print("ADDITIONAL COVERAGE TEST")
        print("=" * 60)

        print(f"Volume: {symbol.Volume()}")
        print(f"Volume High: {symbol.VolumeHigh()}")
        print(f"Volume Low: {symbol.VolumeLow()}")

        print(f"Is Synchronized: {symbol.IsSynchronized()}")
        print(f"Selected: {symbol.Select()}")

        # Test Refresh methods
        print(f"Refresh Symbol: {symbol.Refresh()}")
        print(f"Refresh Rates: {symbol.RefreshRates()}")

        # Test Tick Values
        print(f"Tick Value: {symbol.TickValue()}")
        print(f"Tick Profit: {symbol.TickValueProfit()}")
        print(f"Margin Initial: {symbol.MarginInitial()}")
        print(f"Margin Maintenance: {symbol.MarginMaintenance()}")
        print(f"Margin Long: {symbol.MarginLong()}")
        print(f"Margin Short: {symbol.MarginShort()}")
        print(f"Margin Limit: {symbol.MarginLimit()}")
        print(f"Margin Stop: {symbol.MarginStop()}")
        print(f"Margin Stop Limit: {symbol.MarginStopLimit()}")

        # Test direct info access
        print(f"Info Double (Bid): {symbol.InfoDouble('bid')}")
        print(f"Info Integer (Digits): {symbol.InfoInteger('digits')}")
        print(f"Info String (Name): {symbol.InfoString('name')}")


    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()


