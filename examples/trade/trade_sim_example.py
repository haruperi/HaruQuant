"""
Example usage of C++ CTrade (simulator execution).

This does not execute real MT5 orders.
"""

import os
import sys

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Allow loading local C++ bridge build (hqt_engine.pyd + dependent DLLs).
BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import get_mt5_api
from apps.simulation.data import SymbolInfoSimulator
import hqt_engine.sim as csim

mt5 = get_mt5_api()


def retcode_description(code: int) -> str:
    names = {
        10008: "PLACED",
        10009: "DONE",
        10010: "DONE_PARTIAL",
        10011: "ERROR",
        10013: "INVALID",
        10014: "INVALID_VOLUME",
        10016: "INVALID_STOPS",
        10019: "NO_MONEY",
        10035: "INVALID_ORDER",
        10036: "POSITION_CLOSED",
    }
    return f"{code} ({names.get(code, 'UNKNOWN')})"


def build_symbol(symbol_name: str, symbol_id: int) -> csim.SymbolInfo:
    sim = SymbolInfoSimulator()
    sim.symbol = symbol_name
    if symbol_name == "EURUSD":
        sim.bid = 1.10000
        sim.ask = 1.10010
    elif symbol_name == "GBPUSD":
        sim.bid = 1.27000
        sim.ask = 1.27012
    sym = sim.to_cpp()
    sym.symbol = symbol_name
    sym.symbol_id = symbol_id
    if sym.point <= 0.0:
        sym.point = 0.00001
    if sym.digits <= 0:
        sym.digits = 5
    if sym.volume_min <= 0.0:
        sym.volume_min = 0.01
    if sym.volume_max <= 0.0:
        sym.volume_max = 100.0
    if sym.trade_contract_size <= 0.0:
        sym.trade_contract_size = 100000.0
    return sym


def main():
    print("=" * 70)
    print("Trade Example (C++ CTrade Simulator Execution)")
    print("=" * 70)
    print("Note: This example uses C++ simulator execution only.")
    print()

    trade = csim.CTrade(10000.0, "USD", 100)

    eur = build_symbol("EURUSD", 1)
    gbp = build_symbol("GBPUSD", 2)
    trade.RegisterSymbol(eur)
    trade.RegisterSymbol(gbp)

    trade.SetExpertMagicNumber(12345)
    trade.SetDeviationInPoints(10)
    trade.SetTypeFillingBySymbol("EURUSD")

    print("=" * 70)
    print("Example 1: Open Position")
    print("=" * 70)
    print()

    bid = eur.Bid()
    ask = eur.Ask()
    point = eur.Point()

    print("Current EURUSD prices:")
    print(f"  Bid: {bid:.5f}")
    print(f"  Ask: {ask:.5f}")
    print()

    buy_price = ask
    sl_buy = buy_price - (50 * point)
    tp_buy = buy_price + (100 * point)

    if trade.PositionOpen(
        symbol="EURUSD",
        order_type=int(mt5.ORDER_TYPE_BUY),  # type: ignore[arg-type]
        volume=0.1,
        price=buy_price,
        sl=sl_buy,
        tp=tp_buy,
        comment="Example buy order",
    ):
        print("[OK] Position opened successfully")
        print(f"  Order: #{trade.ResultOrder()}")
        print(f"  Deal: #{trade.ResultDeal()}")
        print(f"  Volume: {trade.ResultVolume()}")
        print(f"  Price: {trade.ResultPrice()}")
    else:
        print("[FAIL] Failed to open position")
        print(f"  Retcode: {retcode_description(trade.ResultRetcode())}")
        print(f"  Comment: {trade.ResultComment()}")

    print()
    print("=" * 70)
    print("Example 2: Modify + Close")
    print("=" * 70)
    print()

    new_sl = buy_price - (30 * point)
    new_tp = buy_price + (150 * point)
    if trade.PositionModify(symbol="EURUSD", sl=new_sl, tp=new_tp):
        print("[OK] Position modified successfully")
    else:
        print("[FAIL] Position modify failed")

    if trade.PositionClose(symbol="EURUSD"):
        print("[OK] Position closed successfully")
    else:
        print("[FAIL] Position close failed")

    print()
    print("=" * 70)
    print("Example 3: Pending Order")
    print("=" * 70)
    print()

    gbp_bid = gbp.Bid()
    gbp_ask = gbp.Ask()
    gbp_point = gbp.Point()
    limit_price = gbp_ask - (50 * gbp_point)
    sl_limit = limit_price - (100 * gbp_point)
    tp_limit = limit_price + (150 * gbp_point)

    if trade.OrderOpen(
        symbol="GBPUSD",
        order_type=int(mt5.ORDER_TYPE_BUY_LIMIT),  # type: ignore[arg-type]
        volume=0.05,
        limit_price=limit_price,
        sl=sl_limit,
        tp=tp_limit,
        comment="Pending buy limit",
    ):
        print("[OK] Pending order placed successfully")
    else:
        print("[FAIL] Pending order failed")


if __name__ == "__main__":
    main()

