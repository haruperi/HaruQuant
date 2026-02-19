"""
Example usage of C++ OrderInfo (Active Orders) with different providers.
"""

import os
import sys
from datetime import datetime

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (hqt_engine.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
import hqt_engine.sim as csim

mt5 = get_mt5_api()


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def _load_live_orders(simulator: "csim.TradeSimulator") -> None:
    orders = mt5.orders_get()
    if orders is None:
        return
    for o in orders:
        row = csim.OrderInfo()
        row.ticket = int(getattr(o, "ticket", 0))
        row.symbol = str(getattr(o, "symbol", ""))
        row.magic = int(getattr(o, "magic", 0))
        row.position_id = int(getattr(o, "position_id", 0))
        row.type = int(getattr(o, "type", 0))
        row.state = int(getattr(o, "state", 0))
        row.volume_initial = float(getattr(o, "volume_initial", 0.0))
        row.volume_current = float(getattr(o, "volume_current", 0.0))
        row.price_open = float(getattr(o, "price_open", 0.0))
        row.price_current = float(getattr(o, "price_current", 0.0))
        row.price_stoplimit = float(getattr(o, "price_stoplimit", 0.0))
        row.sl = float(getattr(o, "sl", 0.0))
        row.tp = float(getattr(o, "tp", 0.0))
        row.set_time_setup(int(getattr(o, "time_setup", 0)), int(getattr(o, "time_setup_msc", 0)))
        row.set_time_expiration(int(getattr(o, "time_expiration", 0)))
        row.set_time_done(int(getattr(o, "time_done", 0)), int(getattr(o, "time_done_msc", 0)))
        row.set_type_filling(int(getattr(o, "type_filling", 0)))
        row.set_type_time(int(getattr(o, "type_time", 0)))
        row.comment = str(getattr(o, "comment", ""))
        simulator.upsert_order_info(row)


def main():
    print("=" * 70)
    print("OrderInfo Example (Active Orders)")
    print("=" * 70)
    print()

    creds = get_mt5_credentials()

    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
    )
    if not connected:
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print("Connected successfully!")
    print()

    # CHOOSE YOUR OPTION
    # Option 1: Live Trading with MT5 (Default)
    simulator = csim.TradeSimulator()
    _load_live_orders(simulator)
    print("Using: MT5 Live Connection")

    # Option 2: Simulator
    # simulator = csim.TradeSimulator()
    # o1 = csim.OrderInfo()
    # o1.ticket = 5001
    # o1.symbol = "EURUSD"
    # o1.type = 2
    # o1.volume_initial = 0.1
    # o1.volume_current = 0.1
    # o1.price_open = 1.0500
    # o1.set_time_setup(int(datetime.now().timestamp()))
    # simulator.upsert_order_info(o1)

    # o2 = csim.OrderInfo()
    # o2.ticket = 5002
    # o2.symbol = "GBPUSD"
    # o2.type = 3
    # o2.volume_initial = 0.2
    # o2.volume_current = 0.2
    # o2.price_open = 1.3000
    # o2.set_time_setup(int(datetime.now().timestamp()))
    # simulator.upsert_order_info(o2)
    # print("Using: Simulator (Simulated Active Orders)")

    print()

    orders = simulator.orders_info_get()
    total = len(orders)

    print("\n" + "=" * 60)
    print(f"Total orders: {total}")

    for i, order in enumerate(orders):
        print(f"\n{i + 1}. Order #{order.Ticket()}")
        print(f"   Symbol: {order.Symbol()}")
        print(f"   Type: {order.TypeDescription()}")
        print(f"   State: {order.StateDescription()}")
        print(f"   Volume: {order.VolumeCurrent():.2f}")
        print(f"   Price: {order.PriceOpen()}")
        print(
            f"   Formatted: #{order.Ticket()} {order.TypeDescription()} {order.Symbol()} {order.VolumeInitial()} at {order.PriceOpen()}"
        )

        print(f"   Ticket: {order.Ticket()}")
        print(f"   Magic: {order.Magic()}")
        print(f"   Position ID: {order.PositionId()}")
        print(f"   Position By ID: {order.PositionById()}")
        print(f"   External ID: {order.ExternalId()}")

        print(f"   Type: {order.TypeDescription()} ({order.Type()})")
        print(f"   State: {order.StateDescription()} ({order.State()})")
        print(f"   Filling: {order.TypeFillingDescription()} ({order.TypeFilling()})")
        print(f"   Time Type: {order.TypeTimeDescription()} ({order.TypeTime()})")

        print(f"   Time Setup: {order.TimeSetup()} (MSC: {order.TimeSetupMsc()})")
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
        ticket_to_select = orders[0].Ticket()
        selected = simulator.orders_info_get(ticket=ticket_to_select)
        if selected:
            order = selected[0]
            print(f"Selected order #{ticket_to_select}:")
            print(f"  Symbol: {order.Symbol()}")
            print(f"  Comment: {order.Comment()}")
            print(f"  Filling: {order.TypeFillingDescription()}")
            print(f"  Time Type: {order.TypeTimeDescription()}")
        else:
            print(f"Order #{ticket_to_select} not found")
    else:
        print("No orders to select.")

    print("\n" + "=" * 60)
    print("Example 3: State Management")
    print("=" * 60)
    print("OrderInfo does not implement state snapshot methods.")

    print("\n" + "=" * 60)
    print("Iterating all orders:")
    print(f"Total orders: {total}")
    for i, order in enumerate(orders):
        print(
            f"#{i + 1}: #{order.Ticket()} {order.TypeDescription()} {order.Symbol()} {order.VolumeInitial()} at {order.PriceOpen()}"
        )
        print(f"    State: {order.StateDescription()}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
