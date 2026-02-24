"""
Example usage of active orders with MT5/Tester backend parity.
"""

import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
import haruquant.core as core

mt5 = get_mt5_api()


def _order_value(order, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(order, attr_name):
        return getattr(order, attr_name)
    if method_name and hasattr(order, method_name):
        return getattr(order, method_name)()
    return default


def _safe_long(value: int | float | None) -> int:
    if value is None:
        return 0
    v = int(value)
    lo = -(2**31)
    hi = (2**31) - 1
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _seed_tester_orders(now: datetime) -> list[core.OrderInfo]:
    o1 = core.OrderInfo()
    o1.SetTicket(5001)
    o1.SetSymbol("EURUSD")
    o1.SetType(2)
    o1.SetState(1)
    o1.SetVolumeInitial(0.1)
    o1.SetVolumeCurrent(0.1)
    o1.SetPriceOpen(1.0500)
    o1.SetTimeSetup(int(now.timestamp()))
    o1.SetTimeSetupMsc(int(now.timestamp()))

    o2 = core.OrderInfo()
    o2.SetTicket(5002)
    o2.SetSymbol("GBPUSD")
    o2.SetType(3)
    o2.SetState(1)
    o2.SetVolumeInitial(0.2)
    o2.SetVolumeCurrent(0.2)
    o2.SetPriceOpen(1.3000)
    o2.SetTimeSetup(int(now.timestamp()))
    o2.SetTimeSetupMsc(int(now.timestamp()))
    return [o1, o2]


def _mt5_orders_to_core() -> list[core.OrderInfo]:
    rows = mt5.orders_get()
    if rows is None:
        return []

    out: list[core.OrderInfo] = []
    for r in rows:
        o = core.OrderInfo()
        o.SetTicket(_safe_long(getattr(r, "ticket", 0)))
        o.SetTimeSetup(_safe_long(getattr(r, "time_setup", 0)))
        o.SetTimeSetupMsc(_safe_long(getattr(r, "time_setup_msc", getattr(r, "time_setup", 0))))
        o.SetTimeDone(_safe_long(getattr(r, "time_done", 0)))
        o.SetTimeDoneMsc(_safe_long(getattr(r, "time_done_msc", getattr(r, "time_done", 0))))
        o.SetTimeExpiration(_safe_long(getattr(r, "time_expiration", 0)))
        o.SetType(_safe_long(getattr(r, "type", 0)))
        o.SetTypeTime(_safe_long(getattr(r, "type_time", 0)))
        o.SetTypeFilling(_safe_long(getattr(r, "type_filling", 0)))
        o.SetState(_safe_long(getattr(r, "state", 0)))
        o.SetMagic(_safe_long(getattr(r, "magic", 0)))
        o.SetReason(_safe_long(getattr(r, "reason", 0)))
        o.SetPositionId(_safe_long(getattr(r, "position_id", 0)))
        o.SetPositionById(_safe_long(getattr(r, "position_by_id", 0)))
        o.SetVolumeInitial(float(getattr(r, "volume_initial", 0.0)))
        o.SetVolumeCurrent(float(getattr(r, "volume_current", 0.0)))
        o.SetPriceOpen(float(getattr(r, "price_open", 0.0)))
        o.SetSl(float(getattr(r, "sl", 0.0)))
        o.SetTp(float(getattr(r, "tp", 0.0)))
        o.SetPriceCurrent(float(getattr(r, "price_current", 0.0)))
        o.SetPriceStopLimit(float(getattr(r, "price_stoplimit", 0.0)))
        o.SetSymbol(str(getattr(r, "symbol", "")))
        o.SetComment(str(getattr(r, "comment", "")))
        out.append(o)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["tester", "mt5"], default="tester")
    args = parser.parse_args()
    backend = args.backend

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
        orders = _mt5_orders_to_core()
        print("Using: MT5 backend")
    else:
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5 (required for base account in tester mode).")
            return
        mt5_account = client.account_info()
        account = core.AccountInfo(mt5_account)
        _backtest_simulator = core.BacktestSimulator(account)
        orders = _seed_tester_orders(datetime.now())
        print("Using: Tester backend")
    print()
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
