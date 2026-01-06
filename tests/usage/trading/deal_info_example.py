"""
Example usage of DealInfo with different providers.

This example demonstrates two ways to use DealInfo:
1. MT5DealProvider - Live trading with MT5 connection
2. BacktestDealProvider - Backtest with simulated deals

Simply uncomment the provider you want to use.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import (
    DealInfo,
    MT5DealProvider,
    BacktestDealProvider,
    DealType,
    DealEntry,
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
    print("=" * 70)
    print("DealInfo Example")
    print("=" * 70)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
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
        print()

        # ============================================================
        # CHOOSE YOUR PROVIDER (uncomment one option)
        # ============================================================

        # Option 1: Live Trading with MT5 (last 30 days)
        now = datetime.now()
        start = now - timedelta(days=30)
        provider = MT5DealProvider(client, date_from=start, date_to=now)
        print("Using: MT5DealProvider (Live Trading - Last 30 Days)")

        # Option 2: Backtesting with Simulated Deals
        # provider = BacktestDealProvider()
        # provider.add_deal(
        #     ticket=2001,
        #     order=1001,
        #     time=datetime.now(),
        #     deal_type=DealType.BUY,
        #     entry=DealEntry.IN,
        #     symbol="EURUSD",
        #     volume=0.1,
        #     price=1.1000,
        #     commission=-0.70,
        #     swap=0.0,
        #     profit=0.0,
        #     magic=12345,
        #     position_id=1001,
        #     comment="Entry deal"
        # )
        # provider.add_deal(
        #     ticket=2002,
        #     order=1002,
        #     time=datetime.now(),
        #     deal_type=DealType.SELL,
        #     entry=DealEntry.OUT,
        #     symbol="EURUSD",
        #     volume=0.1,
        #     price=1.1050,
        #     commission=-0.70,
        #     swap=-0.50,
        #     profit=50.0,
        #     magic=12345,
        #     position_id=1001,
        #     comment="Exit deal"
        # )
        # print("Using: BacktestDealProvider (Simulated Deals)")

        print()

        # Create DealInfo instance
        deal = DealInfo(provider)

        # Example 1: Iterate through all deals
        print("\n" + "=" * 70)
        print("Example 1: All Historical Deals")
        print("=" * 70)

        total_deals = deal.total_deals()
        print(f"Total deals: {total_deals}\n")

        for i in range(total_deals):
            if deal.select_by_index(i):
                print(f"{i + 1}. {deal.format_deal()}")
                print(f"   Type: {deal.type_description()}")
                print(f"   Entry: {deal.entry_description()}")
                print(f"   Time: {deal.time()}")
                if deal.deal_type() in [DealType.BUY, DealType.SELL]:
                    print(f"   Price: {deal.price()}")
                    print(f"   Commission: ${deal.commission():.2f}")
                    print(f"   Profit: ${deal.profit():.2f}")

                # Check additional properties
                print(f"   Magic: {deal.magic()}")
                print(f"   Order: {deal.order()}")
                print(f"   Position ID: {deal.position_id()}")
                print(f"   Time MSC: {deal.time_msc()}")
                print(f"   Entry Enum: {deal.entry()}")
                print(f"   Comment: {deal.comment()}")
                print(f"   External ID: {deal.external_id()}")

                # Test format helpers
                print(f"   Format Action: {DealInfo.format_action(deal.deal_type())}")
                print(f"   Format Entry: {DealInfo.format_entry(deal.entry())}")

        # Example 2: Statistics
        print("\n" + "=" * 70)
        print("Example 2: Trading Statistics")
        print("=" * 70)

        total_profit = 0.0
        total_commission = 0.0
        total_swap = 0.0

        for i in range(deal.total_deals()):
            if deal.select_by_index(i):
                total_profit += deal.profit()
                total_commission += deal.commission()
                total_swap += deal.swap()

        print(f"Total Profit: ${total_profit:.2f}")
        print(f"Total Commission: ${total_commission:.2f}")
        print(f"Total Swap: ${total_swap:.2f}")
        print(f"Net Result: ${total_profit + total_commission + total_swap:.2f}")

        # Example 3: Filter by symbol (Manual implementation since DictProvider logic is simple)
        print("\n" + "=" * 70)
        print("Example 3: Deals by Symbol (Manual Filter)")
        print("=" * 70)

        target_symbol = "EURUSD"
        print(f"Deals for {target_symbol}:")
        count = 0
        for i in range(deal.total_deals()):
            if deal.select_by_index(i):
                if deal.symbol() == target_symbol:
                    print(
                        f"  #{deal.ticket()} {deal.type_description()} {deal.volume()} lots P/L: {deal.profit()}"
                    )
                    count += 1
        if count == 0:
            print("  No deals found.")

        print("\n" + "=" * 70)
        print("Example Complete")
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
