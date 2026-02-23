"""
Example usage of Deal history with MT5/Tester backend parity.

Backend modes:
1. backend = "mt5": read deals directly from MT5 with history_deals_get()
2. backend = "tester": seed C++ tester deals, then read with history_deals_get()
"""

import os
import sys
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
from apps.utils.logger import logger
import haruquant.sim as csim

mt5 = get_mt5_api()


def _load_live_deals(simulator: "csim.TradeSimulator", start: datetime, end: datetime) -> None:
    deals = mt5.history_deals_get(start, end)
    if deals is None:
        return
    for d in deals:
        row = csim.DealInfo()
        row.ticket = int(getattr(d, "ticket", 0))
        row.order = int(getattr(d, "order", 0))
        row.position_id = int(getattr(d, "position_id", 0))
        row.symbol = str(getattr(d, "symbol", ""))
        row.magic = int(getattr(d, "magic", 0))
        row.type = int(getattr(d, "type", 0))
        row.entry = int(getattr(d, "entry", 0))
        row.set_time(int(getattr(d, "time", 0)), int(getattr(d, "time_msc", 0)))
        row.volume = float(getattr(d, "volume", 0.0))
        row.price = float(getattr(d, "price", 0.0))
        row.commission = float(getattr(d, "commission", 0.0))
        row.swap = float(getattr(d, "swap", 0.0))
        row.profit = float(getattr(d, "profit", 0.0))
        row.comment = str(getattr(d, "comment", ""))
        simulator.upsert_deal_info(row)

def _seed_tester_deals(simulator: "csim.TradeSimulator", now: datetime) -> None:
    d1 = csim.DealInfo()
    d1.ticket = 2001
    d1.order = 1001
    d1.position_id = 1001
    d1.symbol = "GBPUSD"
    d1.type = 0
    d1.entry = 0
    d1.set_time(int(now.timestamp()) - 60)
    d1.volume = 0.1
    d1.price = 1.1000
    d1.commission = -1.20
    d1.swap = 0.0
    d1.profit = 0.0
    d1.comment = "Entry deal"
    simulator.upsert_deal_info(d1)

    d2 = csim.DealInfo()
    d2.ticket = 2002
    d2.order = 1002
    d2.position_id = 1001
    d2.symbol = "EURUSD"
    d2.type = 1
    d2.entry = 1
    d2.set_time(int(now.timestamp()) - 30)
    d2.volume = 0.1
    d2.price = 1.1050
    d2.commission = -1.20
    d2.swap = -0.10
    d2.profit = 50.0
    d2.comment = "Exit deal"
    simulator.upsert_deal_info(d2)


def _deal_value(deal, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(deal, attr_name):
        return getattr(deal, attr_name)
    if method_name and hasattr(deal, method_name):
        return getattr(deal, method_name)()
    return default


def main():
    backend = "tester"  # set to: "mt5" or "tester"

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
        simulator = mt5
        print("Using: MT5 backend")
    else:
        simulator = csim.TradeSimulator()
        _seed_tester_deals(simulator, now)
        print("Using: Tester backend")
    print()

    deals = simulator.history_deals_get(start, now) or []

    deals = sorted(
        deals,
        key=lambda x: int(_deal_value(x, "time_msc", "TimeMsc", 0) or 0),
    )

    print("\n" + "=" * 70)
    print("Example 1: All Historical Deals")
    print("=" * 70)

    total_deals = len(deals)
    print(f"Total deals: {total_deals}\n")

    for i, deal in enumerate(deals):
        deal_time = int(_deal_value(deal, "time", "Time", 0) or 0)
        t = datetime.fromtimestamp(deal_time) if deal_time > 0 else "N/A"
        print(f"{i + 1}. Ticket {_deal_value(deal, 'ticket', 'Ticket', 0)}")
        print(f"   Type: {_deal_value(deal, 'type', 'DealType', 0)}")
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
        print("   External ID: N/A")
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
                f"{_deal_value(deal, 'type', 'DealType', 0)} "
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
