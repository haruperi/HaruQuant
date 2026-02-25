"""
Example usage of PositionInfo with MT5/Tester backend parity.
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


def _pos_value(pos, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(pos, attr_name):
        return getattr(pos, attr_name)
    if method_name and hasattr(pos, method_name):
        return getattr(pos, method_name)()
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


def _seed_tester_positions(now: datetime, account: core.AccountInfo) -> None:
    p1 = core.PositionInfo(account)
    p1.SetSymbol("EURUSD")
    p1.SetTicket(3001)
    p1.SetIdentifier(3001)
    p1.SetType(0)
    p1.SetVolume(1.0)
    p1.SetPriceOpen(1.1000)
    p1.SetPriceCurrent(1.1010)
    p1.SetTime(int(now.timestamp()))
    p1.SetTimeMsc(int(now.timestamp()))
    p1.SetProfit(10.0)

    p2 = core.PositionInfo(account)
    p2.SetSymbol("USDJPY")
    p2.SetTicket(3002)
    p2.SetIdentifier(3002)
    p2.SetType(1)
    p2.SetVolume(0.5)
    p2.SetPriceOpen(145.00)
    p2.SetPriceCurrent(144.80)
    p2.SetTime(int(now.timestamp()))
    p2.SetTimeMsc(int(now.timestamp()))
    p2.SetProfit(20.0)


def _positions_get(api, symbol=None, group=None, ticket=None):
    if ticket is not None:
        rows = api.positions_get(ticket=ticket)
    elif symbol is not None:
        rows = api.positions_get(symbol=symbol)
    elif group is not None:
        rows = api.positions_get(group=group)
    else:
        rows = api.positions_get()
    if rows is None:
        return []
    return list(rows)


def _positions_total(api) -> int:
    return int(api.positions_total())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["tester", "mt5"], default="tester")
    args = parser.parse_args()
    backend = args.backend

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
        _seed_tester_positions(datetime.now(), account)
        print("Using: Tester backend")
    print()
    positions = _positions_get(api)
    total = _positions_total(api)

    print("\n" + "=" * 70)
    print("Example 1: All Open Positions")
    print("=" * 70)
    print(f"Total positions: {total}\n")

    for i, position in enumerate(positions):
        print(f"{i + 1}. Ticket {_pos_value(position, 'identifier', 'Identifier', 0)}")
        print(f"   Symbol: {_pos_value(position, 'symbol', 'Symbol', '')}")
        print(f"   Type: {_pos_value(position, 'type', 'Type', 0)}")
        print(f"   Volume: {_pos_value(position, 'volume', 'Volume', 0.0)}")
        print(f"   Open Price: {_pos_value(position, 'price_open', 'PriceOpen', 0.0)}")
        print(f"   Current Price: {_pos_value(position, 'price_current', 'PriceCurrent', 0.0)}")
        print(f"   Profit: ${float(_pos_value(position, 'profit', 'Profit', 0.0)):.2f}")
        print(f"   Swap: ${float(_pos_value(position, 'swap', 'Swap', 0.0)):.2f}")
        print(
            f"   SL: {_pos_value(position, 'sl', 'Sl', 0.0)} "
            f"TP: {_pos_value(position, 'tp', 'Tp', 0.0)}"
        )
        print(f"   Comment: {_pos_value(position, 'comment', 'Comment', '')}")
        print("-" * 30)

    print("\n" + "=" * 60)
    print("Selecting by Symbol 'EURUSD'")
    print("=" * 60)
    eur = _positions_get(api, symbol="EURUSD")
    if eur:
        position = eur[0]
        print("Found EURUSD position:")
        print(f"  Identifier: {_pos_value(position, 'identifier', 'Identifier', 0)}")
        print(f"  Profit: {_pos_value(position, 'profit', 'Profit', 0.0)}")
    else:
        print("No EURUSD position found.")

    print("\n" + "=" * 60)
    print("Filter by Group '*USD*'")
    print("=" * 60)
    usd_group = _positions_get(api, group="*USD*")
    print(f"positions_get(group='*USD*') -> {len(usd_group)} row(s)")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
