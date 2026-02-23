"""
Example usage of PositionInfo with MT5/Tester backend parity.
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


def _pos_value(pos, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(pos, attr_name):
        return getattr(pos, attr_name)
    if method_name and hasattr(pos, method_name):
        return getattr(pos, method_name)()
    return default


def _seed_tester_positions(simulator: "csim.TradeSimulator", now: datetime) -> None:
    p1 = csim.PositionInfo()
    p1.ticket = 3001
    p1.identifier = 3001
    p1.symbol = "EURUSD"
    p1.type = 0
    p1.volume = 1.0
    p1.price_open = 1.1000
    p1.price_current = 1.1010
    p1.set_time(int(now.timestamp()))
    simulator.upsert_position_info(p1)

    p2 = csim.PositionInfo()
    p2.ticket = 3002
    p2.identifier = 3002
    p2.symbol = "USDJPY"
    p2.type = 1
    p2.volume = 0.5
    p2.price_open = 145.00
    p2.price_current = 144.80
    p2.set_time(int(now.timestamp()))
    simulator.upsert_position_info(p2)


def main():
    backend = "tester"  # set to: "mt5" or "tester"

    print("=" * 70)
    print("PositionInfo Example (MT5/Tester Parity)")
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
        _seed_tester_positions(simulator, datetime.now())
        print("Using: Tester backend")
    print()

    positions = simulator.positions_get() or []

    print("\n" + "=" * 70)
    print("Example 1: All Open Positions")
    print("=" * 70)
    print(f"Total positions: {len(positions)}\n")

    for i, position in enumerate(positions):
        print(f"{i + 1}. Ticket {_pos_value(position, 'identifier', 'Identifier', 0)}")
        print(f"   Symbol: {_pos_value(position, 'symbol', 'Symbol', '')}")
        print(f"   Type: {_pos_value(position, 'type', 'PositionType', 0)}")
        print(f"   Volume: {_pos_value(position, 'volume', 'Volume', 0.0)}")
        print(f"   Open Price: {_pos_value(position, 'price_open', 'PriceOpen', 0.0)}")
        print(f"   Current Price: {_pos_value(position, 'price_current', 'PriceCurrent', 0.0)}")
        print(f"   Profit: ${float(_pos_value(position, 'profit', 'Profit', 0.0)):.2f}")
        print(f"   Swap: ${float(_pos_value(position, 'swap', 'Swap', 0.0)):.2f}")
        print(
            f"   SL: {_pos_value(position, 'sl', 'StopLoss', 0.0)} "
            f"TP: {_pos_value(position, 'tp', 'TakeProfit', 0.0)}"
        )
        print(f"   Comment: {_pos_value(position, 'comment', 'Comment', '')}")
        print("-" * 30)

    print("\n" + "=" * 60)
    print("Selecting by Symbol 'EURUSD'")
    print("=" * 60)
    eur = simulator.positions_get(symbol="EURUSD") or []
    if eur:
        position = eur[0]
        print("Found EURUSD position:")
        print(f"  Identifier: {_pos_value(position, 'identifier', 'Identifier', 0)}")
        print(f"  Profit: {_pos_value(position, 'profit', 'Profit', 0.0)}")
    else:
        print("No EURUSD position found.")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
