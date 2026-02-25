"""Example usage of Deal history with MT5/Tester backend parity."""

import os
import sys
import argparse
from datetime import datetime, timedelta

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (haruquant shim on top of haruquant.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
import haruquant.core as core

mt5 = get_mt5_api()


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


def _seed_tester_deals(now: datetime, account: core.AccountInfo) -> None:
    d1 = core.DealInfo(account)
    d1.SetTicket(2001)
    d1.SetOrder(1001)
    d1.SetPositionId(1001)
    d1.SetSymbol("GBPUSD")
    d1.SetType(0)
    d1.SetEntry(0)
    d1.SetTime(int(now.timestamp()) - 60)
    d1.SetTimeMsc(int(now.timestamp()) - 60)
    d1.SetVolume(0.1)
    d1.SetPrice(1.1000)
    d1.SetCommission(-1.20)
    d1.SetSwap(0.0)
    d1.SetProfit(0.0)
    d1.SetComment("Entry deal")

    d2 = core.DealInfo(account)
    d2.SetTicket(2002)
    d2.SetOrder(1002)
    d2.SetPositionId(1001)
    d2.SetSymbol("EURUSD")
    d2.SetType(1)
    d2.SetEntry(1)
    d2.SetTime(int(now.timestamp()) - 30)
    d2.SetTimeMsc(int(now.timestamp()) - 30)
    d2.SetVolume(0.1)
    d2.SetPrice(1.1050)
    d2.SetCommission(-1.20)
    d2.SetSwap(-0.10)
    d2.SetProfit(50.0)
    d2.SetComment("Exit deal")


def _mt5_deals_to_tester_state(start: datetime, end: datetime, account: core.AccountInfo) -> int:
    rows = mt5.history_deals_get(start, end)
    if rows is None:
        return 0

    count = 0
    for d in rows:
        deal = core.DealInfo(account)
        deal.SetTicket(_safe_long(getattr(d, "ticket", 0)))
        deal.SetOrder(_safe_long(getattr(d, "order", 0)))
        deal.SetPositionId(_safe_long(getattr(d, "position_id", 0)))
        deal.SetType(_safe_long(getattr(d, "type", 0)))
        deal.SetEntry(_safe_long(getattr(d, "entry", 0)))
        deal.SetMagic(_safe_long(getattr(d, "magic", 0)))
        deal.SetTime(_safe_long(getattr(d, "time", 0)))
        deal.SetTimeMsc(_safe_long(getattr(d, "time_msc", getattr(d, "time", 0))))
        deal.SetVolume(float(getattr(d, "volume", 0.0)))
        deal.SetPrice(float(getattr(d, "price", 0.0)))
        deal.SetCommission(float(getattr(d, "commission", 0.0)))
        deal.SetSwap(float(getattr(d, "swap", 0.0)))
        deal.SetProfit(float(getattr(d, "profit", 0.0)))
        deal.SetFee(float(getattr(d, "fee", 0.0)))
        deal.SetSymbol(str(getattr(d, "symbol", "")))
        deal.SetComment(str(getattr(d, "comment", "")))
        deal.SetExternalId(str(getattr(d, "external_id", "")))
        count += 1
    return count


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
    parser.add_argument("--backend", choices=["tester", "mt5"], default="tester")
    args = parser.parse_args()
    backend = args.backend

    print("=" * 70)
    print("DealInfo Example (MT5/Tester Parity)")
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
        api = mt5
        print("Using: MT5 backend")
    else:
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5 (required for base account in tester mode).")
            return
        mt5_account = client.account_info()
        account = core.AccountInfo(mt5_account)
        api = core.BacktestSimulator(account)
        copied = _mt5_deals_to_tester_state(start, now, account)
        if copied == 0:
            _seed_tester_deals(now, account)
        print("Using: Tester backend")
    print()

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

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")

if __name__ == "__main__":
    main()
