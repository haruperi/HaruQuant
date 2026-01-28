"""
Example usage of DealInfo with different providers.

This example demonstrates two ways to use DealInfo:
1. DealInfo(api=client) - Live trading with MT5 connection
2. DealInfo(api=simulator) - Simulation with custom simulated deals

Simply uncomment the option you want to use.
"""

import sys
import os
from datetime import datetime, timedelta

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trade import DealInfo
from apps.trade.simulator_data import SimulatorClient, DealInfoSimulator


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
    print("=" * 70)
    print("DealInfo Example")
    print("=" * 70)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not connected:
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print(f"Connected successfully!")
    print()

    # ============================================================
    # CHOOSE YOUR OPTION
    # ============================================================

    # Option 1: Live Trading with MT5 (Default)
    # deal = DealInfo()
    # print("Using: MT5 Live Connection (Last 30 Days)")

    # Option 2: Simulator with Simulated Deals (Uncomment to use)
    sim_deals = {
        2001: DealInfoSimulator(
            ticket=2001, order=1001, volume=0.1, price=1.1000, 
            symbol="EURUSD", comment="Entry deal", profit=0.0, type=0 # Buy
        ),
        2002: DealInfoSimulator(
            ticket=2002, order=1002, volume=0.1, price=1.1050, 
            symbol="EURUSD", comment="Exit deal", profit=50.0, type=1 # Sell
        )
    }
    simulator = SimulatorClient(deals_data=sim_deals)
    deal = DealInfo(api=simulator)
    print("Using: Simulator (Simulated Deals)")

    print()

    # Select History Range (Last 30 days)
    now = datetime.now()
    start = now - timedelta(days=30)
    
    if not deal.HistorySelect(start, now):
        print("Failed to select history.")
        return

    # Example 1: Iterate through all deals
    print("\n" + "=" * 70)
    print("Example 1: All Historical Deals")
    print("=" * 70)

    total_deals = deal.TotalDeals()
    print(f"Total deals: {total_deals}\n")

    for i in range(total_deals):
        if deal.SelectByIndex(i):
            print(f"{i + 1}. Ticket {deal.Ticket()}")
            print(f"   Type: {deal.DealTypeDescription()}")
            print(f"   Entry: {deal.EntryDescription()}")
            print(f"   Time: {deal.Time()}")
            # Check price for Buy/Sell
            # Helper logic: standard library checks DealType implies price relevance
            print(f"   Price: {deal.Price()}")
            print(f"   Commission: ${deal.Commission():.2f}")
            print(f"   Profit: ${deal.Profit():.2f}")

            # Check additional properties
            print(f"   Magic: {deal.Magic()}")
            print(f"   Order: {deal.Order()}")
            print(f"   Position ID: {deal.PositionId()}")
            print(f"   Time MSC: {deal.TimeMsc()}")
            print(f"   Comment: {deal.Comment()}")
            print(f"   External ID: {deal.ExternalId()}")
            print("-" * 30)

    # Example 2: Statistics
    print("\n" + "=" * 70)
    print("Example 2: Trading Statistics")
    print("=" * 70)

    total_profit = 0.0
    total_commission = 0.0
    total_swap = 0.0

    for i in range(deal.TotalDeals()):
        if deal.SelectByIndex(i):
            total_profit += deal.Profit()
            total_commission += deal.Commission()
            total_swap += deal.Swap()

    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Total Commission: ${total_commission:.2f}")
    print(f"Total Swap: ${total_swap:.2f}")
    print(f"Net Result: ${total_profit + total_commission + total_swap:.2f}")

    # Example 3: Filter by symbol
    print("\n" + "=" * 70)
    print("Example 3: Deals by Symbol (Manual Filter)")
    print("=" * 70)

    target_symbol = "EURUSD"
    print(f"Deals for {target_symbol}:")
    count = 0
    for i in range(deal.TotalDeals()):
        if deal.SelectByIndex(i):
            if deal.Symbol() == target_symbol:
                print(
                    f"  #{deal.Ticket()} {deal.DealTypeDescription()} {deal.Volume()} lots P/L: {deal.Profit()}"
                )
                count += 1
    if count == 0:
        print("  No deals found.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
