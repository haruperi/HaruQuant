"""
Example usage of OrderInfo (Active Orders) with different providers.
"""

import sys
import os
from datetime import datetime

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client, get_mt5_api
mt5 = get_mt5_api()

from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trade import OrderInfo
from apps.simulation.data import SimulatorClient, OrderInfoSimulator


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("OrderInfo Example (Active Orders)")
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
    # order = OrderInfo(api=client)
    # print("Using: MT5 Live Connection")

    # Option 2: Simulator (Uncomment to use)
    sim_orders = {
        5001: OrderInfoSimulator(ticket=5001, symbol="EURUSD", type=2, volume_initial=0.1, price_open=1.0500), # Buy Limit
        5002: OrderInfoSimulator(ticket=5002, symbol="GBPUSD", type=3, volume_initial=0.2, price_open=1.3000), # Sell Limit
    }
    simulator = SimulatorClient(orders_data=sim_orders)
    order = OrderInfo(api=simulator)
    print("Using: Simulator (Simulated Active Orders)")

    print()


    # Example 1: Iterate through orders
    print("\n" + "=" * 60)

    total = order.Total()
    print(f"Total orders: {total}")

    for i in range(total):
        if order.SelectByIndex(i):
            print(f"\n{i + 1}. Order #{order.Ticket()}")
            print(f"   Symbol: {order.Symbol()}")
            print(f"   Type: {order.TypeDescription()}")
            print(f"   State: {order.StateDescription()}")
            print(f"   Volume: {order.VolumeCurrent():.2f}")
            print(f"   Price: {order.PriceOpen()}")
            print(
                f"   Formatted: #{order.Ticket()} {order.TypeDescription()} {order.Symbol()} {order.VolumeInitial()} at {order.PriceOpen()}"
            )

            # Detailed Properties
            print(f"   Ticket: {order.Ticket()}")
            print(f"   Magic: {order.Magic()}")
            print(f"   Position ID: {order.PositionId()}")
            print(f"   Position By ID: {order.PositionById()}")
            print(f"   External ID: {order.ExternalId()}")

            print(f"   Type: {order.TypeDescription()} ({order.Type()})")
            print(f"   State: {order.StateDescription()} ({order.State()})")
            print(
                f"   Filling: {order.TypeFillingDescription()} ({order.TypeFilling()})"
            )
            print(
                f"   Time Type: {order.TypeTimeDescription()} ({order.TypeTime()})"
            )

            print(
                f"   Time Setup: {order.TimeSetup()} (MSC: {order.TimeSetupMsc()})"
            )
            print(f"   Expiration: {order.TimeExpiration()}")

            print(f"   Vol Initial: {order.VolumeInitial()}")
            print(f"   Vol Current: {order.VolumeCurrent()}")
            print(f"   Price Open: {order.PriceOpen()}")
            print(f"   Price Current: {order.PriceCurrent()}")
            print(f"   Stop Limit: {order.PriceStopLimit()}")
            print(f"   SL: {order.StopLoss()}")
            print(f"   TP: {order.TakeProfit()}")

            print(f"   Comment: {order.Comment()}")

    print("\n" + "=" * 60)
    print("Example 2: Select Order by Ticket")
    print("=" * 60)

    if total > 0:
        # Select first order to get its ticket
        if order.SelectByIndex(0):
            ticket_to_select = order.Ticket()
            if order.Select(ticket_to_select):
                print(f"Selected order #{ticket_to_select}:")
                print(f"  Symbol: {order.Symbol()}")
                print(f"  Comment: {order.Comment()}")
                print(f"  Filling: {order.TypeFillingDescription()}")
                print(f"  Time Type: {order.TypeTimeDescription()}")
            else:
                print(f"Order #{ticket_to_select} not found")
    else:
        print("No orders to select.")

    # Example 3: State management
    print("\n" + "=" * 60)
    print("Example 3: State Management")
    print("=" * 60)
    print("OrderInfo does not implement state snapshot methods.")

    # Example 4: Iterate all
    print("\n" + "=" * 60)
    print("Iterating all orders:")

    total = order.Total()
    print(f"Total orders: {total}")

    for i in range(total):
        if order.SelectByIndex(i):
            print(
                f"#{i+1}: #{order.Ticket()} {order.TypeDescription()} {order.Symbol()} {order.VolumeInitial()} at {order.PriceOpen()}"
            )
            print(f"    State: {order.StateDescription()}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
