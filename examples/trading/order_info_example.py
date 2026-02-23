"""
Example usage of active orders with MT5/Tester backend parity.
"""

import os
import sys
from datetime import datetime

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


def _order_value(order, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(order, attr_name):
        return getattr(order, attr_name)
    if method_name and hasattr(order, method_name):
        return getattr(order, method_name)()
    return default


def _seed_tester_orders(simulator: "csim.TradeSimulator", now: datetime) -> None:
    o1 = csim.OrderInfo()
    o1.ticket = 5001
    o1.symbol = "EURUSD"
    o1.type = 2
    o1.volume_initial = 0.1
    o1.volume_current = 0.1
    o1.price_open = 1.0500
    o1.set_time_setup(int(now.timestamp()))
    simulator.upsert_order_info(o1)

    o2 = csim.OrderInfo()
    o2.ticket = 5002
    o2.symbol = "GBPUSD"
    o2.type = 3
    o2.volume_initial = 0.2
    o2.volume_current = 0.2
    o2.price_open = 1.3000
    o2.set_time_setup(int(now.timestamp()))
    simulator.upsert_order_info(o2)


def main():
    backend = "tester"  # set to: "mt5" or "tester"

    print("=" * 70)
    print("OrderInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    client = None
    if backend == "mt5":
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5.")
            return

    if backend == "mt5":
        simulator = mt5
        print("Using: MT5 backend")
    else:
        simulator = csim.TradeSimulator()
        _seed_tester_orders(simulator, datetime.now())
        print("Using: Tester backend")
    print()

    orders = simulator.orders_get() or []
    total = len(orders)

    print("\n" + "=" * 60)
    print(f"Total orders: {total}")

    for i, order in enumerate(orders):
        print(f"\n{i + 1}. Order #{_order_value(order, 'ticket', 'Ticket', 0)}")
        print(f"   Symbol: {_order_value(order, 'symbol', 'Symbol', '')}")
        print(f"   Type: {_order_value(order, 'type', 'Type', 0)}")
        print(f"   State: {_order_value(order, 'state', 'State', 0)}")
        print(f"   Volume: {float(_order_value(order, 'volume_current', 'VolumeCurrent', 0.0)):.2f}")
        print(f"   Price: {_order_value(order, 'price_open', 'PriceOpen', 0.0)}")
        print(
            f"   Formatted: #{_order_value(order, 'ticket', 'Ticket', 0)} "
            f"{_order_value(order, 'type', 'Type', 0)} "
            f"{_order_value(order, 'symbol', 'Symbol', '')} "
            f"{_order_value(order, 'volume_initial', 'VolumeInitial', 0.0)} at "
            f"{_order_value(order, 'price_open', 'PriceOpen', 0.0)}"
        )

    print("\n" + "=" * 60)
    print("Example 2: Select Order by Ticket")
    print("=" * 60)

    if total > 0:
        ticket_to_select = _order_value(orders[0], "ticket", "Ticket", 0)
        selected = simulator.orders_get(ticket=ticket_to_select) or []
        if selected:
            order = selected[0]
            print(f"Selected order #{ticket_to_select}:")
            print(f"  Symbol: {_order_value(order, 'symbol', 'Symbol', '')}")
            print(f"  Comment: {_order_value(order, 'comment', 'Comment', '')}")
        else:
            print(f"Order #{ticket_to_select} not found")
    else:
        print("No orders to select.")

    print("\n" + "=" * 60)
    print("Iterating all orders:")
    print(f"Total orders: {total}")
    for i, order in enumerate(orders):
        print(
            f"#{i + 1}: #{_order_value(order, 'ticket', 'Ticket', 0)} "
            f"{_order_value(order, 'type', 'Type', 0)} "
            f"{_order_value(order, 'symbol', 'Symbol', '')} "
            f"{_order_value(order, 'volume_initial', 'VolumeInitial', 0.0)} at "
            f"{_order_value(order, 'price_open', 'PriceOpen', 0.0)}"
        )
        print(f"    State: {_order_value(order, 'state', 'State', 0)}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
