"""
Example usage of active orders with MT5/Tester backend parity.
"""

import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.simulation.engine import Engine
from services.execution.core import OrderInfo

def _order_value(order, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(order, attr_name):
        return getattr(order, attr_name)
    if method_name and hasattr(order, method_name):
        return getattr(order, method_name)()
    return default


def _seed_tester_orders(now: datetime, engine_instance: Engine) -> None:
    o1 = OrderInfo()
    o1.ticket = 5001
    o1.symbol = "EURUSD"
    o1.type = 2
    o1.state = 1
    o1.volume_initial = 0.1
    o1.volume_current = 0.1
    o1.price_open = 1.0500
    o1.time_setup = int(now.timestamp())
    o1.time_setup_msc = int(now.timestamp())
    engine_instance.state.trading_orders.append(o1)

    o2 = OrderInfo()
    o2.ticket = 5002
    o2.symbol = "GBPUSD"
    o2.type = 3
    o2.state = 1
    o2.volume_initial = 0.2
    o2.volume_current = 0.2
    o2.price_open = 1.3000
    o2.time_setup = int(now.timestamp())
    o2.time_setup_msc = int(now.timestamp())
    engine_instance.state.trading_orders.append(o2)


def _orders_get(api, symbol=None, group=None, ticket=None):
    if ticket is not None:
        rows = api.orders_get(ticket=ticket)
    elif symbol is not None:
        rows = api.orders_get(symbol=symbol)
    elif group is not None:
        rows = api.orders_get(group=group)
    else:
        rows = api.orders_get()
    if rows is None:
        return []
    return list(rows)


def _orders_total(api) -> int:
    return int(api.orders_total())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend

    print("=" * 70)
    print("OrderInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    engine_instance = Engine(backend=backend)
    api = engine_instance.api

    if backend == "sim":
        _seed_tester_orders(datetime.now(), engine_instance)
        print("Using: Tester backend")
    else:
        print("Using: MT5 backend")
    orders = _orders_get(api)
    total = _orders_total(api)

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

    if len(orders) > 0:
        ticket_to_select = _order_value(orders[0], "ticket", "Ticket", 0)
        selected = [o for o in orders if int(_order_value(o, "ticket", "Ticket", 0)) == int(ticket_to_select)]
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
    print("Example 3: Filter by Symbol")
    print("=" * 60)
    symbol_orders = _orders_get(api, symbol="EURUSD")
    print(f"orders_get(symbol='EURUSD') -> {len(symbol_orders)} row(s)")

    print("\n" + "=" * 60)
    print("Example 4: Filter by Group")
    print("=" * 60)
    group_orders = _orders_get(api, group="*USD*")
    print(f"orders_get(group='*USD*') -> {len(group_orders)} row(s)")

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

    print("\nShutting down MT5 connection...")
    engine_instance.client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
