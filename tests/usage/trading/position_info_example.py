"""
Example usage of PositionInfo with different providers.

This example demonstrates two ways to use PositionInfo:
1. MT5PositionProvider - Live trading with MT5 connection
2. BacktestPositionProvider - Backtest with simulated positions

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
    PositionInfo,
    MT5PositionProvider,
    BacktestPositionProvider,
    PositionType,
)
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


def main():
    print("=" * 60)
    print("PositionInfo Example")
    print("=" * 60)
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
        print(f"Connection state: {client.connection_state.value}")
        print()

        # ============================================================
        # CHOOSE YOUR PROVIDER (uncomment one option)
        # ============================================================

        # Option 1: Live Trading with MT5
        provider = MT5PositionProvider(client)
        print("Using: MT5PositionProvider (Live Trading)")

        # Option 2: Backtesting with Simulated Positions
        # provider = BacktestPositionProvider()
        # provider.add_position(
        #     ticket=1001,
        #     symbol="EURUSD",
        #     position_type=PositionType.BUY,
        #     volume=0.1,
        #     price_open=1.1000,
        #     stop_loss=1.0950,
        #     take_profit=1.1050,
        #     time=datetime.now(),
        #     magic=12345,
        #     comment="Backtest position"
        # )
        # provider.add_position(
        #     ticket=1002,
        #     symbol="GBPUSD",
        #     position_type=PositionType.SELL,
        #     volume=0.2,
        #     price_open=1.2500,
        #     stop_loss=1.2550,
        #     take_profit=1.2450,
        #     time=datetime.now(),
        #     magic=12345,
        #     comment="Backtest position"
        # )
        # print("Using: BacktestPositionProvider (Simulated Positions)")

        print()

        # Create PositionInfo instance
        position = PositionInfo(provider)

        total_positions = position.total_positions()
        print(f"\nTotal positions: {total_positions}")

        # Iterate through positions
        print("\n" + "-" * 60)
        print("POSITIONS LIST")
        print("-" * 60)

        for i in range(total_positions):
            if position.select_by_index(i):
                print(f"Position #{i+1}:")
                print(f"  Ticket:       {position.ticket()}")
                print(f"  Symbol:       {position.symbol()}")
                print(f"  Type:         {position.type_description()}")
                print(f"  Volume:       {position.volume()}")
                print(f"  Open Price:   {position.price_open()}")
                print(f"  Current Price:{position.price_current()}")
                print(f"  Profit:       {position.profit()}")
                print(f"  Comment:      {position.comment()}")
                print(f"  Formatted:    {position.format_position()}")

                # Detailed Properties
                print(f"  Time:         {position.time()} (MSC: {position.time_msc()})")
                print(
                    f"  Update:       {position.time_update()} (MSC: {position.time_update_msc()})"
                )

                print(f"  Type Enum:    {position.position_type()}")
                print(f"  Magic:        {position.magic()}")
                print(f"  Identifier:   {position.identifier()}")

                print(f"  Stop Loss:    {position.stop_loss()}")
                print(f"  Take Profit:  {position.take_profit()}")
                print(f"  Swap:         {position.swap()}")
                # Note: Commission is deprecated in position info. Use deal history instead:
                # print(f"  Commission:   {position.commission()}")
                print(f"  Note: For commission data, use DealInfo with deal history")
                print("-" * 30)

        # Example of selecting by symbol
        print("\n" + "=" * 60)
        print("Selecting by Symbol 'EURUSD'")
        print("=" * 60)
        if position.select("EURUSD"):
            print(f"Found EURUSD position:")
            print(f"  Ticket: {position.ticket()}")
            print(f"  Profit: {position.profit()}")
        else:
            print("No EURUSD position found.")

        # Example of selection by ticket and magic
        if position.total_positions() > 0 and position.select_by_index(0):
            ticket = position.ticket()
            magic = position.magic()
            symbol = position.symbol()

            print(
                f"\nTesting Select by Ticket ({ticket}): {'Success' if position.select_by_ticket(ticket) else 'Failed'}"
            )
            print(
                f"Testing Select by Magic ({symbol}, {magic}): {'Success' if position.select_by_magic(symbol, magic) else 'Failed'}"
            )

        # Example of state management
        if position.total_positions() > 0:
            position.select_by_index(0)
            print("\n" + "=" * 60)
            print(f"State Management for Ticket {position.ticket()}")
            print("=" * 60)
            position.store_state()
            print("State stored. Checking for changes...")
            if position.check_state():
                print("State changed!")
            else:
                print("State unchanged.")

        print("\n" + "=" * 60)
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
