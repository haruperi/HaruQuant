"""Example usage of HistoryOrderInfo with MT5/Tester backend parity."""

import os
import sys
import argparse
from datetime import datetime, timedelta

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


def _hist_value(order, attr_name: str, method_name: str | None = None, default=None):
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


def _seed_tester_history_orders(now: datetime) -> list[core.HistoryOrderInfo]:
    o1 = core.HistoryOrderInfo()
    o1.SetTicket(1001)
    o1.SetSymbol("EURUSD")
    o1.SetType(0)
    o1.SetState(4)
    o1.SetVolumeInitial(1.0)
    o1.SetVolumeCurrent(0.0)
    o1.SetPriceOpen(1.1000)
    o1.SetTimeSetup(int(now.timestamp()) - 120)
    o1.SetTimeDone(int(now.timestamp()) - 60)
    o1.SetTimeSetupMsc(int(now.timestamp()) - 120)
    o1.SetTimeDoneMsc(int(now.timestamp()) - 60)

    o2 = core.HistoryOrderInfo()
    o2.SetTicket(1002)
    o2.SetSymbol("GBPUSD")
    o2.SetType(1)
    o2.SetState(2)
    o2.SetVolumeInitial(0.5)
    o2.SetVolumeCurrent(0.5)
    o2.SetPriceOpen(1.2500)
    o2.SetTimeSetup(int(now.timestamp()) - 90)
    o2.SetTimeDone(int(now.timestamp()) - 30)
    o2.SetTimeSetupMsc(int(now.timestamp()) - 90)
    o2.SetTimeDoneMsc(int(now.timestamp()) - 30)
    return [o1, o2]


def _mt5_history_orders_to_core(start: datetime, end: datetime) -> list[core.HistoryOrderInfo]:
    rows = mt5.history_orders_get(start, end)
    if rows is None:
        return []

    out: list[core.HistoryOrderInfo] = []
    for r in rows:
        o = core.HistoryOrderInfo()
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
        orders = _mt5_history_orders_to_core(start, now)
    else:
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5 (required for base account in tester mode).")
            return
        mt5_account = client.account_info()
        account = core.AccountInfo(mt5_account)
        _backtest_simulator = core.BacktestSimulator(account)
        orders = _seed_tester_history_orders(now)
        print("Using: Tester backend")
    print()
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
        print(f"   Type: {_hist_value(order, 'type', 'Type', 0)}")
        print(f"   Symbol: {_hist_value(order, 'symbol', 'Symbol', '')}")
        print(
            f"   Volume: {_hist_value(order, 'volume_current', 'VolumeCurrent', 0.0)}/"
            f"{_hist_value(order, 'volume_initial', 'VolumeInitial', 0.0)}"
        )
        print(f"   Price: {_hist_value(order, 'price_open', 'PriceOpen', 0.0)}")
        print(
            f"   SL: {_hist_value(order, 'sl', 'StopLoss', 0.0)}, "
            f"TP: {_hist_value(order, 'tp', 'Tp', 0.0)}"
        )
        print(f"   Magic: {_hist_value(order, 'magic', 'Magic', 0)}")
        print(f"   Position By ID: {_hist_value(order, 'position_id', 'PositionId', 0)}")
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
