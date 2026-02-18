"""
Example usage of C++ DealInfo with different providers.

This example demonstrates two ways to source deals:
1. Live MT5 history loaded into C++ TradeSimulator as DealInfo
2. Pure simulated DealInfo objects loaded directly into C++ TradeSimulator
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


def main():
    print("=" * 70)
    print("DealInfo Example (C++ TradeSimulator)")
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
    # Option 1: Live MT5 deals loaded into C++ simulator (default)
    # simulator = csim.TradeSimulator()
    # _load_live_deals(simulator, start, now)
    # print("Using: MT5 Live History -> C++ TradeSimulator")

    # Option 2: Simulator with custom DealInfo objects
    simulator = csim.TradeSimulator()
    d1 = csim.DealInfo()
    d1.ticket = 2001
    d1.order = 1001
    d1.position_id = 1001
    d1.symbol = "EURUSD"
    d1.type = 0
    d1.entry = 0
    d1.set_time(int(now.timestamp()))
    d1.volume = 0.1
    d1.price = 1.1000
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
    d2.set_time(int(now.timestamp()))
    d2.volume = 0.1
    d2.price = 1.1050
    d2.profit = 50.0
    d2.comment = "Exit deal"
    simulator.upsert_deal_info(d2)
    print("Using: Simulator (Simulated DealInfo)")

    print()

    deals = simulator.history_deal_infos_get()
    deals = sorted(deals, key=lambda x: int(x.TimeMsc()))

    print("\n" + "=" * 70)
    print("Example 1: All Historical Deals")
    print("=" * 70)

    total_deals = len(deals)
    print(f"Total deals: {total_deals}\n")

    for i, deal in enumerate(deals):
        t = datetime.fromtimestamp(int(deal.Time())) if int(deal.Time()) > 0 else "N/A"
        print(f"{i + 1}. Ticket {deal.Ticket()}")
        print(f"   Type: {deal.DealTypeDescription()}")
        print(f"   Entry: {deal.EntryDescription()}")
        print(f"   Time: {t}")
        print(f"   Price: {deal.Price()}")
        print(f"   Commission: ${deal.Commission():.2f}")
        print(f"   Profit: ${deal.Profit():.2f}")
        print(f"   Magic: {deal.Magic()}")
        print(f"   Order: {deal.Order()}")
        print(f"   Position ID: {deal.PositionId()}")
        print(f"   Time MSC: {deal.TimeMsc()}")
        print(f"   Comment: {deal.Comment()}")
        print("   External ID: N/A")
        print("-" * 30)

    print("\n" + "=" * 70)
    print("Example 2: Trading Statistics")
    print("=" * 70)

    total_profit = sum(float(d.Profit()) for d in deals)
    total_commission = sum(float(d.Commission()) for d in deals)
    total_swap = sum(float(d.Swap()) for d in deals)

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
        if deal.Symbol() == target_symbol:
            print(
                f"  #{deal.Ticket()} {deal.DealTypeDescription()} {deal.Volume()} lots P/L: {deal.Profit()}"
            )
            count += 1
    if count == 0:
        print("  No deals found.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
