"""
Example usage of PositionInfo with MT5/Tester backend parity.
"""

import os
import sys
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from haruquant.simulation import Engine
from haruquant.execution import PositionInfo

def _pos_value(pos, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(pos, attr_name):
        return getattr(pos, attr_name)
    if method_name and hasattr(pos, method_name):
        return getattr(pos, method_name)()
    return default


def _seed_tester_positions(now: datetime, engine_instance: Engine) -> None:
    p1 = PositionInfo()
    p1.symbol = "EURUSD"
    p1.ticket = 3001
    p1.identifier = 3001
    p1.type = 0
    p1.volume = 1.0
    p1.price_open = 1.1000
    p1.price_current = 1.1010
    p1.time = int(now.timestamp())
    p1.time_msc = int(now.timestamp())
    p1.profit = 10.0
    engine_instance.state.trading_deals.append(p1)

    p2 = PositionInfo()
    p2.symbol = "USDJPY"
    p2.ticket = 3002
    p2.identifier = 3002
    p2.type = 1
    p2.volume = 0.5
    p2.price_open = 145.00
    p2.price_current = 144.80
    p2.time = int(now.timestamp())
    p2.time_msc = int(now.timestamp())
    p2.profit = 20.0
    engine_instance.state.trading_deals.append(p2)


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
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend

    print("=" * 70)
    print("PositionInfo Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    engine_instance = Engine(backend=backend)
    api = engine_instance.api

    if backend == "sim":
        _seed_tester_positions(datetime.now(), engine_instance)
        print("Using: Tester backend")
    else:
        print("Using: MT5 backend")
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

    print("\nShutting down MT5 connection...")
    engine_instance.client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
