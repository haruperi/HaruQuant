"""
Example usage of C++ HistoryOrderInfo with different providers.
"""

import os
import sys
from datetime import datetime, timedelta

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


def _load_live_history_orders(simulator: "csim.TradeSimulator", start: datetime, end: datetime) -> None:
    orders = mt5.history_orders_get(start, end)
    if orders is None:
        return
    for o in orders:
        row = csim.HistoryOrderInfo()
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
        simulator.upsert_history_order_info(row)


def main():
    print("=" * 70)
    print("HistoryOrderInfo Example (C++ TradeSimulator)")
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

    now = datetime.now()
    start = now - timedelta(days=30)

    # CHOOSE YOUR OPTION
    # Option 1: Live history orders into C++ simulator (default)
    # simulator = csim.TradeSimulator()
    # _load_live_history_orders(simulator, start, now)
    # print("Using: MT5 Live History Orders -> C++ TradeSimulator")

    # Option 2: Simulator with custom HistoryOrderInfo
    simulator = csim.TradeSimulator()
    o1 = csim.HistoryOrderInfo()
    o1.ticket = 1001
    o1.symbol = "EURUSD"
    o1.type = 0
    o1.state = 4
    o1.volume_initial = 1.0
    o1.volume_current = 0.0
    o1.price_open = 1.1000
    o1.set_time_setup(int(now.timestamp()))
    o1.set_time_done(int(now.timestamp()))
    simulator.upsert_history_order_info(o1)

    o2 = csim.HistoryOrderInfo()
    o2.ticket = 1002
    o2.symbol = "GBPUSD"
    o2.type = 1
    o2.state = 2
    o2.volume_initial = 0.5
    o2.volume_current = 0.5
    o2.price_open = 1.2500
    o2.set_time_setup(int(now.timestamp()))
    o2.set_time_done(int(now.timestamp()))
    simulator.upsert_history_order_info(o2)
    print("Using: Simulator (Simulated History Orders)")

    print()

    orders = simulator.history_order_infos_get()
    orders = sorted(orders, key=lambda x: int(x.TimeSetupMsc()))

    print("\n" + "=" * 70)
    print("Example 1: All Historical Orders")
    print("=" * 70)
    print(f"Total orders: {len(orders)}\n")

    for i, order in enumerate(orders):
        print(f"{i + 1}. Ticket #{order.Ticket()} {order.Symbol()} {order.OrderTypeDescription()}")
        print(f"   State: {order.StateDescription()}")
        print(f"   Setup: {order.TimeSetup()}")
        print(f"   Done: {order.TimeDone()}")
        print(f"   Type: {order.OrderTypeDescription()}")
        print(f"   Symbol: {order.Symbol()}")
        print(f"   Volume: {order.VolumeCurrent()}/{order.VolumeInitial()}")
        print(f"   Price: {order.PriceOpen()}")
        print(f"   SL: {order.StopLoss()}, TP: {order.TakeProfit()}")
        print(f"   Magic: {order.Magic()}")
        print(f"   Position By ID: {order.PositionByID()}")
        print(f"   External ID: {order.ExternalID()}")
        print(f"   Vol Initial: {order.VolumeInitial()}")
        print(f"   Vol Current: {order.VolumeCurrent()}")
        print(f"   Price Open: {order.PriceOpen()}")
        print(f"   Price Current: {order.PriceCurrent()}")
        print(f"   Stop Limit: {order.PriceStopLimit()}")
        print(f"   SL: {order.StopLoss()}")
        print(f"   TP: {order.TakeProfit()}")
        print(f"   Comment: {order.Comment()}")
        print("-" * 30)

    print("\n" + "=" * 70)
    print("Example 2: History Order Statistics")
    print("=" * 70)

    filled_count = sum(1 for o in orders if o.WasFilled())
    canceled_count = sum(1 for o in orders if o.WasCanceled())
    total_vol = sum(float(o.VolumeInitial()) for o in orders)
    print(f"Filled: {filled_count}")
    print(f"Canceled: {canceled_count}")
    print(f"Total Volume Ordered: {total_vol:.2f}")

    print("\n" + "=" * 70)
    print("Example 3: String Representation")
    print("=" * 70)
    if orders:
        print(f"Ticket #{orders[0].Ticket()} {orders[0].Symbol()} {orders[0].OrderTypeDescription()}")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
