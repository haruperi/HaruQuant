"""
Example usage of HistoryOrderInfo with MT5/Tester backend parity.
"""

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
import haruquant.sim as csim

mt5 = get_mt5_api()


def _hist_value(order, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(order, attr_name):
        return getattr(order, attr_name)
    if method_name and hasattr(order, method_name):
        return getattr(order, method_name)()
    return default


def _seed_tester_history_orders(simulator: "csim.TradeSimulator", now: datetime) -> None:
    o1 = csim.HistoryOrderInfo()
    o1.ticket = 1001
    o1.symbol = "EURUSD"
    o1.type = 0
    o1.state = 4
    o1.volume_initial = 1.0
    o1.volume_current = 0.0
    o1.price_open = 1.1000
    o1.set_time_setup(int(now.timestamp()) - 120)
    o1.set_time_done(int(now.timestamp()) - 60)
    simulator.upsert_history_order_info(o1)

    o2 = csim.HistoryOrderInfo()
    o2.ticket = 1002
    o2.symbol = "GBPUSD"
    o2.type = 1
    o2.state = 2
    o2.volume_initial = 0.5
    o2.volume_current = 0.5
    o2.price_open = 1.2500
    o2.set_time_setup(int(now.timestamp()) - 90)
    o2.set_time_done(int(now.timestamp()) - 30)
    simulator.upsert_history_order_info(o2)


def main():
    backend = "tester"  # set to: "mt5" or "tester"

    print("=" * 70)
    print("HistoryOrderInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    client = None
    if backend == "mt5":
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5.")
            return

    now = datetime.now()
    start = now - timedelta(days=30)

    if backend == "mt5":
        simulator = mt5
        print("Using: MT5 backend")
    else:
        simulator = csim.TradeSimulator()
        _seed_tester_history_orders(simulator, now)
        print("Using: Tester backend")
    print()

    orders = simulator.history_orders_get(start, now) or []
    orders = sorted(
        orders,
        key=lambda x: int(_hist_value(x, "time_setup_msc", "TimeSetupMsc", 0) or 0),
    )

    print("\n" + "=" * 70)
    print("Example 1: All Historical Orders")
    print("=" * 70)
    print(f"Total orders: {len(orders)}\n")

    for i, order in enumerate(orders):
        print(
            f"{i + 1}. Ticket #{_hist_value(order, 'ticket', 'Ticket', 0)} "
            f"{_hist_value(order, 'symbol', 'Symbol', '')}"
        )
        print(f"   State: {_hist_value(order, 'state', 'State', 0)}")
        print(f"   Setup: {_hist_value(order, 'time_setup', 'TimeSetup', 0)}")
        print(f"   Done: {_hist_value(order, 'time_done', 'TimeDone', 0)}")
        print(f"   Type: {_hist_value(order, 'type', 'OrderType', 0)}")
        print(f"   Symbol: {_hist_value(order, 'symbol', 'Symbol', '')}")
        print(
            f"   Volume: {_hist_value(order, 'volume_current', 'VolumeCurrent', 0.0)}/"
            f"{_hist_value(order, 'volume_initial', 'VolumeInitial', 0.0)}"
        )
        print(f"   Price: {_hist_value(order, 'price_open', 'PriceOpen', 0.0)}")
        print(
            f"   SL: {_hist_value(order, 'sl', 'StopLoss', 0.0)}, "
            f"TP: {_hist_value(order, 'tp', 'TakeProfit', 0.0)}"
        )
        print(f"   Magic: {_hist_value(order, 'magic', 'Magic', 0)}")
        print(f"   Position By ID: {_hist_value(order, 'position_by_id', 'PositionByID', 0)}")
        print("-" * 30)

    print("\n" + "=" * 70)
    print("Example 2: History Order Statistics")
    print("=" * 70)

    filled_count = sum(1 for o in orders if int(_hist_value(o, "state", "State", 0)) == 4)
    canceled_count = sum(1 for o in orders if int(_hist_value(o, "state", "State", 0)) == 2)
    total_vol = sum(float(_hist_value(o, "volume_initial", "VolumeInitial", 0.0)) for o in orders)
    print(f"Filled: {filled_count}")
    print(f"Canceled: {canceled_count}")
    print(f"Total Volume Ordered: {total_vol:.2f}")

    print("\n" + "=" * 70)
    print("Example 3: String Representation")
    print("=" * 70)
    if orders:
        print(
            f"Ticket #{_hist_value(orders[0], 'ticket', 'Ticket', 0)} "
            f"{_hist_value(orders[0], 'symbol', 'Symbol', '')}"
        )

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
