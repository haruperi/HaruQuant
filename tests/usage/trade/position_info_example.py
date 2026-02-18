"""
Example usage of PositionInfo with different providers.
"""

import sys
import os
from datetime import datetime

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from apps.trade import PositionInfo
from apps.simulation.data import TradeSimulator, PositionInfoSimulator


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
    print("PositionInfo Example")
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
    # position = PositionInfo()
    # print("Using: MT5 Live Connection")

    # Option 2: Simulator (Uncomment to use)
    sim_positions = {
        3001: PositionInfoSimulator(ticket=3001, symbol="EURUSD", type=0, volume=1.0, price_open=1.1000, profit=100.0),
        3002: PositionInfoSimulator(ticket=3002, symbol="USDJPY", type=1, volume=0.5, price_open=145.00, profit=-50.0),
    }
    simulator = TradeSimulator(positions_data=sim_positions)
    position = PositionInfo(api=simulator)
    print("Using: Simulator (Simulated Positions)")

    print()

    # Example 1: Iterate through all positions
    print("\n" + "=" * 70)
    print("Example 1: All Open Positions")
    print("=" * 70)

    total_positions = position.Total()
    print(f"Total positions: {total_positions}\n")

    for i in range(total_positions):
        if position.SelectByIndex(i):
            print(f"{i + 1}. Ticket {position.Identifier()}") # Use Identifier() or Ticket? Identifier usually.
            print(f"   Symbol: {position.Symbol()}")
            print(f"   Type: {position.TypeDescription()}")
            print(f"   Volume: {position.Volume()}")
            print(f"   Open Price: {position.PriceOpen()}")
            print(f"   Current Price: {position.PriceCurrent()}")
            print(f"   Profit: ${position.Profit():.2f}")
            print(f"   Swap: ${position.Swap():.2f}")
            print(f"   SL: {position.StopLoss()} TP: {position.TakeProfit()}")
            print(f"   Comment: {position.Comment()}")
            print("-" * 30)

        # Example of selecting by symbol
        print("\n" + "=" * 60)
        print("Selecting by Symbol 'EURUSD'")
        print("=" * 60)
        if position.Select("EURUSD"):
            print(f"Found EURUSD position:")
            print(f"  Identifier: {position.Identifier()}")
            print(f"  Profit: {position.Profit()}")
        else:
            print("No EURUSD position found.")

        # Example of selection by ticket and magic
        if position.Total() > 0 and position.SelectByIndex(0):
            ticket = position.Identifier()
            magic = position.Magic()
            symbol = position.Symbol()

            print(
                f"\nTesting Select by Ticket ({ticket}): {'Success' if position.SelectByTicket(ticket) else 'Failed'}"
            )
            print(
                f"Testing Select by Magic ({symbol}, {magic}): {'Success' if position.SelectByMagic(symbol, magic) else 'Failed'}"
            )

        # Example of state management
        if position.Total() > 0:
            position.SelectByIndex(0)
            print("\n" + "=" * 60)
            print(f"State Management for Identifier {position.Identifier()}")
            print("=" * 60)
            position.StoreState()
            print("State stored. Checking for changes...")
            if position.CheckState():
                print("State changed!")
            else:
                print("State unchanged.")

        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()


