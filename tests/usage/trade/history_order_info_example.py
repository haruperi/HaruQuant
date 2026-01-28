"""
Example usage of HistoryOrderInfo with different providers.
"""

import sys
import os
from datetime import datetime, timedelta

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client, get_mt5_api
mt5 = get_mt5_api()

from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trade import HistoryOrderInfo
from apps.trade.simulator_data import SimulatorClient, HistoryOrderInfoSimulator


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("HistoryOrderInfo Example")
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
    # history_order = HistoryOrderInfo()
    # print("Using: MT5 Live Connection (Last 30 Days)")

    # Option 2: Simulator (Uncomment to use)
    sim_orders = {
        1001: HistoryOrderInfoSimulator(ticket=1001, symbol="EURUSD", type=0, volume_initial=1.0, state=4), # Filled Buy
        1002: HistoryOrderInfoSimulator(ticket=1002, symbol="GBPUSD", type=1, volume_initial=0.5, state=5), # Canceled Sell
    }
    simulator = SimulatorClient(history_orders_data=sim_orders)
    history_order = HistoryOrderInfo(api=simulator)
    print("Using: Simulator (Simulated History Orders)")

    print()

    # Example 1: Iterate through all historical orders
    print("\n" + "=" * 70)
    print("Example 1: All Historical Orders")
    print("=" * 70)

    # Using total_orders()
    # Select history for the last year + 1 day ahead (to include everything)
    now = datetime.now()
    history_order.HistorySelect(now - timedelta(days=365), now + timedelta(days=1))
    
    total = history_order.HistoryOrdersTotal()
    print(f"Total orders: {total}\n")

    for i in range(total):
        if history_order.SelectByIndex(i):
            print(f"{i + 1}. {history_order.FormatOrder()}")
            print(f"   State: {history_order.StateDescription()}")
            print(f"   Setup: {history_order.TimeSetup()}")
            print(f"   Done: {history_order.TimeDone()}")
            print(f"   Type: {history_order.OrderTypeDescription()}")
            print(f"   Symbol: {history_order.Symbol()}")
            print(f"   Volume: {history_order.VolumeCurrent()}/{history_order.VolumeInitial()}")
            print(f"   Price: {history_order.PriceOpen()}")
            print(f"   SL: {history_order.StopLoss()}, TP: {history_order.TakeProfit()}")
            print(f"   Magic: {history_order.Magic()}")
            print(f"   Position By ID: {history_order.PositionByID()}")
            print(f"   External ID: {history_order.ExternalID()}")

            # Volumes and Prices
            print(f"   Vol Initial: {history_order.VolumeInitial()}")
            print(f"   Vol Current: {history_order.VolumeCurrent()}")
            print(f"   Price Open: {history_order.PriceOpen()}")
            print(f"   Price Current: {history_order.PriceCurrent()}")
            print(f"   Stop Limit: {history_order.PriceStopLimit()}")
            print(f"   SL: {history_order.StopLoss()}")
            print(f"   TP: {history_order.TakeProfit()}")

            # Comment
            print(f"   Comment: {history_order.Comment()}")

            # Test static formatters
            print(
                f"   Format Type: {HistoryOrderInfo.format_type(history_order.OrderType())}"
            )
            print(
                f"   Format Status: {HistoryOrderInfo.format_status(history_order.State())}"
            )
            print(
                f"   Format Filling: {HistoryOrderInfo.format_type_filling(history_order.TypeFilling())}"
            )
            print(
                f"   Format Time: {HistoryOrderInfo.format_type_time(history_order.TypeTime())}"
            )
            if history_order.PriceStopLimit() > 0:
                print(
                    f"   Format Price: {HistoryOrderInfo.format_price(history_order.PriceOpen(), history_order.PriceStopLimit(), 5)}"
                )

        # Example 2: Statistics
    print("\n" + "=" * 70)
    print("Example 2: history_order Statistics")
    print("=" * 70)

    filled_count = 0
    canceled_count = 0
    total_vol = 0.0

    for i in range(total):
        if history_order.SelectByIndex(i):
            total_vol += history_order.VolumeInitial()
            if history_order.State() == getattr(mt5, "ORDER_STATE_FILLED", 4):
                filled_count += 1
            elif history_order.State() == getattr(mt5, "ORDER_STATE_CANCELED", 2):
                canceled_count += 1

    print(f"Filled: {filled_count}")
    print(f"Canceled: {canceled_count}")
    print(f"Total Volume Ordered: {total_vol:.2f}")

    # Example 3: String Representation
    print("\n" + "=" * 70)
    print("Example 3: String Representation")
    print("=" * 70)

    if total > 0 and history_order.SelectByIndex(0):
        print(f"repr(): {repr(history_order)}")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
