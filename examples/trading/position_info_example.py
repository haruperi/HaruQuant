"""
Example usage of C++ PositionInfo with different providers.
"""

import os
import sys
from datetime import datetime

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (hqt_engine.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
from apps.utils.logger import logger
import hqt_engine.sim as csim

mt5 = get_mt5_api()


def _load_live_positions(simulator: "csim.TradeSimulator") -> None:
    positions = mt5.positions_get()
    if positions is None:
        return
    for p in positions:
        row = csim.PositionInfo()
        row.ticket = int(getattr(p, "ticket", 0))
        row.identifier = int(getattr(p, "identifier", row.ticket))
        row.symbol = str(getattr(p, "symbol", ""))
        row.magic = int(getattr(p, "magic", 0))
        row.type = int(getattr(p, "type", 0))
        row.volume = float(getattr(p, "volume", 0.0))
        row.price_open = float(getattr(p, "price_open", 0.0))
        row.price_current = float(getattr(p, "price_current", 0.0))
        row.sl = float(getattr(p, "sl", 0.0))
        row.tp = float(getattr(p, "tp", 0.0))
        row.commission = float(getattr(p, "commission", 0.0))
        row.swap = float(getattr(p, "swap", 0.0))
        row.profit = float(getattr(p, "profit", 0.0))
        row.comment = str(getattr(p, "comment", ""))
        row.set_time(int(getattr(p, "time", 0)), int(getattr(p, "time_msc", 0)))
        row.set_time_update(int(getattr(p, "time_update", 0)), int(getattr(p, "time_update_msc", 0)))
        simulator.upsert_position_info(row)


def main():
    print("=" * 70)
    print("PositionInfo Example")
    print("=" * 70)
    print()

    client = MT5Utils.get_connected_client()

    

    # CHOOSE YOUR OPTION
    # Option 1: Live Trading with MT5 (Default)
    simulator = csim.TradeSimulator()
    _load_live_positions(simulator)
    print("Using: MT5 Live Connection")

    # Option 2: Simulator
    # simulator = csim.TradeSimulator()
    # p1 = csim.PositionInfo()
    # p1.ticket = 3001
    # p1.identifier = 3001
    # p1.symbol = "EURUSD"
    # p1.type = 0
    # p1.volume = 1.0
    # p1.price_open = 1.1000
    # p1.price_current = 1.1010
    # p1.set_time(int(datetime.now().timestamp()))
    # simulator.upsert_position_info(p1)

    # p2 = csim.PositionInfo()
    # p2.ticket = 3002
    # p2.identifier = 3002
    # p2.symbol = "USDJPY"
    # p2.type = 1
    # p2.volume = 0.5
    # p2.price_open = 145.00
    # p2.price_current = 144.80
    # p2.set_time(int(datetime.now().timestamp()))
    # simulator.upsert_position_info(p2)
    # print("Using: Simulator (Simulated Positions)")

    print()

    positions = simulator.positions_info_get()

    print("\n" + "=" * 70)
    print("Example 1: All Open Positions")
    print("=" * 70)
    print(f"Total positions: {len(positions)}\n")

    for i, position in enumerate(positions):
        print(f"{i + 1}. Ticket {position.Identifier()}")
        print(f"   Symbol: {position.Symbol()}")
        print(f"   Type: {position.TypeDescription()}")
        print(f"   Volume: {position.Volume()}")
        print(f"   Open Price: {position.PriceOpen()}")
        print(f"   Current Price: {position.PriceCurrent()}")
        print(f"   Profit: ${position.Profit():.2f}")
        print(f"   Swap: ${position.Swap():.2f}")
        print(f"   SL: {position.StopLoss()} TP: {position.TakeProfit()}")
        print(f"   Comment: {position.Comment()}")
        print("-" * 30)

    print("\n" + "=" * 60)
    print("Selecting by Symbol 'EURUSD'")
    print("=" * 60)
    eur = simulator.positions_info_get(symbol="EURUSD")
    if eur:
        position = eur[0]
        print("Found EURUSD position:")
        print(f"  Identifier: {position.Identifier()}")
        print(f"  Profit: {position.Profit()}")
    else:
        print("No EURUSD position found.")

    if positions:
        first = positions[0]
        ticket = first.Ticket()
        magic = first.Magic()
        symbol = first.Symbol()
        print(f"\nTesting Select by Ticket ({ticket}): {'Success' if first.SelectByTicket(ticket) else 'Failed'}")
        print(f"Testing Select by Magic ({symbol}, {magic}): {'Success' if first.SelectByMagic(symbol, magic) else 'Failed'}")

    if positions:
        first = positions[0]
        print("\n" + "=" * 60)
        print(f"State Management for Identifier {first.Identifier()}")
        print("=" * 60)
        first.StoreState()
        print("State stored. Checking for changes...")
        if first.CheckState():
            print("State changed!")
        else:
            print("State unchanged.")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
