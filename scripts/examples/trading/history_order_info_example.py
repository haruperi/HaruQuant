"""Example usage of HistoryOrderInfo with MT5/Tester backend parity."""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
sys.path.insert(0, PROJECT_ROOT)

from haruquant.simulation import Engine
from haruquant.execution import HistoryOrderInfo


def _hist_value(order, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(order, attr_name):
        return getattr(order, attr_name)
    if method_name and hasattr(order, method_name):
        return getattr(order, method_name)()
    return default


def _seed_tester_history_orders(now: datetime, engine_instance: Engine) -> None:
    o1 = HistoryOrderInfo()
    o1.ticket = 1001
    o1.symbol = "EURUSD"
    o1.type = 0
    o1.state = 4
    o1.volume_initial = 1.0
    o1.volume_current = 0.0
    o1.price_open = 1.1000
    o1.time_setup = int(now.timestamp()) - 120
    o1.time_done = int(now.timestamp()) - 60
    o1.time_setup_msc = int(now.timestamp()) - 120
    o1.time_done_msc = int(now.timestamp()) - 60
    engine_instance.state.trading_history_orders.append(o1)

    o2 = HistoryOrderInfo()
    o2.ticket = 1002
    o2.symbol = "GBPUSD"
    o2.type = 1
    o2.state = 2
    o2.volume_initial = 0.5
    o2.volume_current = 0.5
    o2.price_open = 1.2500
    o2.time_setup = int(now.timestamp()) - 90
    o2.time_done = int(now.timestamp()) - 30
    o2.time_setup_msc = int(now.timestamp()) - 90
    o2.time_done_msc = int(now.timestamp()) - 30
    engine_instance.state.trading_history_orders.append(o2)


def _history_orders_get(api, start=None, end=None, group=None, ticket=None):
    if start is None and end is None and ticket is not None:
        rows = api.history_orders_get(ticket=ticket)
    elif ticket is not None and group is not None:
        rows = api.history_orders_get(start, end, group=group, ticket=ticket)
    elif group is not None:
        rows = api.history_orders_get(start, end, group=group)
    elif ticket is not None:
        rows = api.history_orders_get(start, end, ticket=ticket)
    else:
        rows = api.history_orders_get(start, end)
    if rows is None:
        return []
    return list(rows)


def _history_orders_total(api, start: datetime, end: datetime) -> int:
    return int(api.history_orders_total(start, end))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend

    print("=" * 70)
    print("HistoryOrderInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    engine_instance = Engine(backend=backend)
    api = engine_instance.api

    now = datetime.now()
    start = now - timedelta(days=30)

    if backend == "sim":
        _seed_tester_history_orders(now, engine_instance)
        print("Using: Tester backend")
    else:
        print("Using: MT5 backend")
    orders = _history_orders_get(api, start, now)
    total = _history_orders_total(api, start, now)
    orders = sorted(
        orders,
        key=lambda x: int(_hist_value(x, "time_setup_msc", "TimeSetupMsc", 0) or 0),
    )

    print("\n" + "=" * 70)
    print("Example 1: All Historical Orders")
    print("=" * 70)
    print(f"Total orders: {total}\n")

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
    print("Example 2b: Filter by Group '*USD*'")
    print("=" * 70)
    usd_group = _history_orders_get(api, start, now, group="*USD*")
    print(f"history_orders_get(group='*USD*') -> {len(usd_group)} row(s)")

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

    print("\nShutting down MT5 connection...")
    engine_instance.client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
