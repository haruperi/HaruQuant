"""Example usage of Deal history with MT5/Tester backend parity."""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.services.simulation.engine import Engine
from backend.services.execution.core import DealInfo

def _seed_tester_deals(now: datetime, engine_instance: Engine) -> None:
    d1 = DealInfo()
    d1.ticket = 2001
    d1.order = 1001
    d1.position_id = 1001
    d1.symbol = "GBPUSD"
    d1.type = 0
    d1.entry = 0
    d1.time = int(now.timestamp()) - 60
    d1.time_msc = int(now.timestamp()) - 60
    d1.volume = 0.1
    d1.price = 1.1000
    d1.commission = -1.20
    d1.swap = 0.0
    d1.profit = 0.0
    d1.comment = "Entry deal"
    engine_instance.state.trading_history_deals.append(d1)

    d2 = DealInfo()
    d2.ticket = 2002
    d2.order = 1002
    d2.position_id = 1001
    d2.symbol = "EURUSD"
    d2.type = 1
    d2.entry = 1
    d2.time = int(now.timestamp()) - 30
    d2.time_msc = int(now.timestamp()) - 30
    d2.volume = 0.1
    d2.price = 1.1050
    d2.commission = -1.20
    d2.swap = -0.10
    d2.profit = 50.0
    d2.comment = "Exit deal"
    engine_instance.state.trading_history_deals.append(d2)


def _deal_value(deal, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(deal, attr_name):
        return getattr(deal, attr_name)
    if method_name and hasattr(deal, method_name):
        return getattr(deal, method_name)()
    return default


def _history_deals_get(api, start=None, end=None, group=None, ticket=None):
    if start is None and end is None and ticket is not None:
        rows = api.history_deals_get(ticket=ticket)
    elif ticket is not None and group is not None:
        rows = api.history_deals_get(start, end, group=group, ticket=ticket)
    elif group is not None:
        rows = api.history_deals_get(start, end, group=group)
    elif ticket is not None:
        rows = api.history_deals_get(start, end, ticket=ticket)
    else:
        rows = api.history_deals_get(start, end)
    if rows is None:
        return []
    return list(rows)


def _history_deals_total(api, start: datetime, end: datetime) -> int:
    return int(api.history_deals_total(start, end))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend

    print("=" * 70)
    print("DealInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    engine_instance = Engine(backend=backend)
    api = engine_instance.api

    now = datetime.now()
    start = now - timedelta(days=30)
    
    if backend == "sim":
        _seed_tester_deals(now, engine_instance)
        print("Using: Tester backend")
    else:
        print("Using: MT5 backend")

    deals = _history_deals_get(api, start, now)
    total_deals = _history_deals_total(api, start, now)

    deals = sorted(
        deals,
        key=lambda x: int(_deal_value(x, "time_msc", "TimeMsc", 0) or 0),
    )

    print("\n" + "=" * 70)
    print("Example 1: All Historical Deals")
    print("=" * 70)

    print(f"Total deals: {total_deals}\n")

    for i, deal in enumerate(deals):
        deal_time = int(_deal_value(deal, "time", "Time", 0) or 0)
        t = datetime.fromtimestamp(deal_time) if deal_time > 0 else "N/A"
        print(f"{i + 1}. Ticket {_deal_value(deal, 'ticket', 'Ticket', 0)}")
        print(f"   Type: {_deal_value(deal, 'type', 'Type', 0)}")
        print(f"   Entry: {_deal_value(deal, 'entry', 'Entry', 0)}")
        print(f"   Time: {t}")
        print(f"   Price: {_deal_value(deal, 'price', 'Price', 0.0)}")
        print(f"   Commission: ${float(_deal_value(deal, 'commission', 'Commission', 0.0)):.2f}")
        print(f"   Profit: ${float(_deal_value(deal, 'profit', 'Profit', 0.0)):.2f}")
        print(f"   Magic: {_deal_value(deal, 'magic', 'Magic', 0)}")
        print(f"   Order: {_deal_value(deal, 'order', 'Order', 0)}")
        print(f"   Position ID: {_deal_value(deal, 'position_id', 'PositionId', 0)}")
        print(f"   Time MSC: {_deal_value(deal, 'time_msc', 'TimeMsc', 0)}")
        print(f"   Comment: {_deal_value(deal, 'comment', 'Comment', '')}")
        print(f"   External ID: {_deal_value(deal, 'external_id', 'ExternalId', '')}")
        print("-" * 30)

    print("\n" + "=" * 70)
    print("Example 2: Trading Statistics")
    print("=" * 70)

    total_profit = sum(float(_deal_value(d, "profit", "Profit", 0.0)) for d in deals)
    total_commission = sum(float(_deal_value(d, "commission", "Commission", 0.0)) for d in deals)
    total_swap = sum(float(_deal_value(d, "swap", "Swap", 0.0)) for d in deals)

    print(f"Total Profit: ${total_profit:.2f}")
    print(f"Total Commission: ${total_commission:.2f}")
    print(f"Total Swap: ${total_swap:.2f}")
    print(f"Net Result: ${total_profit + total_commission + total_swap:.2f}")

    print("\n" + "=" * 70)
    print("Example 2b: Filter by Group '*USD*'")
    print("=" * 70)
    usd_group = _history_deals_get(api, start, now, group="*USD*")
    print(f"history_deals_get(group='*USD*') -> {len(usd_group)} row(s)")

    print("\n" + "=" * 70)
    print("Example 3: Deals by Symbol (Manual Filter)")
    print("=" * 70)

    target_symbol = "EURUSD"
    print(f"Deals for {target_symbol}:")
    count = 0
    for deal in deals:
        symbol = _deal_value(deal, "symbol", "Symbol", "")
        if symbol == target_symbol:
            print(
                f"  #{_deal_value(deal, 'ticket', 'Ticket', 0)} "
                f"{_deal_value(deal, 'type', 'Type', 0)} "
                f"{_deal_value(deal, 'volume', 'Volume', 0.0)} lots "
                f"P/L: {_deal_value(deal, 'profit', 'Profit', 0.0)}"
            )
            count += 1
    if count == 0:
        print("  No deals found.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    print("\nShutting down MT5 connection...")
    engine_instance.client.shutdown()
    print("Disconnected.")

if __name__ == "__main__":
    main()
