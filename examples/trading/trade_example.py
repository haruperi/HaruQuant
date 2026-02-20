"""
Unified trade lifecycle example with MT5/Tester backend parity.
"""

import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, Trade, get_mt5_api
from apps.utils.error_description import TradeErrorDescriptions
import hqt_engine.sim as csim

mt5 = get_mt5_api()


def code_text(code: int) -> str:
    return f"{code} ({TradeErrorDescriptions.error_description(code)})"


def mt5_result(trade: "Trade"):
    return SimpleNamespace(
        retcode=trade.ResultRetcode(),
        order=trade.ResultOrder(),
        deal=trade.ResultDeal(),
        volume=trade.ResultVolume(),
        price=trade.ResultPrice(),
        comment=trade.ResultComment(),
    )

def obj_val(obj, attr: str, method: str, default=0):
    if hasattr(obj, attr):
        return getattr(obj, attr)
    if hasattr(obj, method):
        return getattr(obj, method)()
    return default


def seed_tester() -> "csim.TradeSimulator":
    account = csim.AccountInfo(50000.0, "USD", 100)
    account.login = 12345678
    account.name = "Simulator Account"
    account.server = "HQT-SIM"
    account.company = "HaruQuant"
    account.trade_allowed = True
    account.trade_expert = True
    sim = csim.TradeSimulator(account)

    for idx, (name, bid, ask) in enumerate([("EURUSD", 1.10000, 1.10010), ("GBPUSD", 1.27000, 1.27012)], start=1):
        s = csim.SymbolInfo()
        s.symbol_id = idx
        s.symbol = name
        s.digits = 5
        s.point = 0.00001
        s.spread = int(round((ask - bid) / s.point))
        s.spread_float = True
        s.trade_mode = 4
        s.trade_exemode = 2
        s.trade_calc_mode = 0
        s.volume_min = 0.01
        s.volume_max = 100.0
        s.volume_step = 0.01
        s.trade_contract_size = 100000.0
        s.trade_tick_size = s.point
        s.trade_tick_value = 1.0
        s.trade_tick_value_profit = 1.0
        s.trade_tick_value_loss = 1.0
        s.bid = bid
        s.ask = ask
        sim.set_symbol_info(s)

        now_utc = datetime.now(timezone.utc)
        t = csim.SymbolTickData()
        t.time = int(now_utc.timestamp())
        t.time_msc = int(now_utc.timestamp() * 1000.0)
        t.bid = bid
        t.ask = ask
        t.last = (bid + ask) / 2.0
        t.volume = 0
        t.flags = 0
        t.volume_real = 0.0
        sim.set_symbol_tick(name, t)
    return sim


def main():
    backend = "mt5"  # set to: "mt5" or "tester"

    print("=" * 70)
    print("Trade Example (MT5/Tester Parity)")
    print("=" * 70)
    print()

    client = None
    if backend == "mt5":
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5.")
            return
        simulator = mt5
        trade = Trade(mt5)
        trade.SetExpertMagicNumber(12345)
        trade.SetDeviationInPoints(20)
        trade.SetTypeFillingBySymbol("EURUSD")
        trade.SetTypeFillingBySymbol("GBPUSD")
        print("Using: MT5 backend")
    else:
        simulator = seed_tester()
        trade = None
        print("Using: Tester backend")
    print()

    # Example 1: Open Position
    print("=" * 70)
    print("Example 1: Open Position")
    print("=" * 70)
    info = simulator.symbol_info("EURUSD")
    if info is None:
        print("[FAIL] Failed to get EURUSD info")
        return
    buy_price = float(info.ask)
    point = float(info.point)
    sl = buy_price - (50 * point)
    tp = buy_price + (100 * point)
    if backend == "mt5":
        trade.PositionOpen("EURUSD", mt5.ORDER_TYPE_BUY, 0.1, buy_price, sl, tp, "Example open position")
        res = mt5_result(trade)
    else:
        req = csim.TradeRequest()
        req.action = int(mt5.TRADE_ACTION_DEAL)
        req.type = int(mt5.ORDER_TYPE_BUY)
        req.symbol = "EURUSD"
        req.volume = 0.1
        req.price = buy_price
        req.sl = sl
        req.tp = tp
        req.type_time = int(mt5.ORDER_TIME_GTC)
        req.comment = "Example open position"
        res = simulator.order_send(req)
    print(f"Retcode: {code_text(int(res.retcode))}")
    print(f"Order: #{int(res.order)} Deal: #{int(res.deal)}")

    positions = simulator.positions_get(symbol="EURUSD") or []
    if not positions:
        print("[FAIL] No EURUSD position after open")
        return
    pos = positions[0]
    pos_ticket = int(obj_val(pos, "ticket", "Ticket", 0))
    print(f"Position ticket: {pos_ticket}")

    # Example 2: Edit SL/TP
    print()
    print("=" * 70)
    print("Example 2: Edit SL/TP")
    print("=" * 70)
    info = simulator.symbol_info("EURUSD")
    new_sl = float(info.ask) - (30 * point)
    new_tp = float(info.ask) + (150 * point)
    if backend == "mt5":
        trade.PositionModify(symbol="EURUSD", ticket=pos_ticket, sl=new_sl, tp=new_tp)
        res = mt5_result(trade)
    else:
        req = csim.TradeRequest()
        req.action = int(mt5.TRADE_ACTION_SLTP)
        req.order = pos_ticket  # tester route maps this as position ticket
        req.symbol = "EURUSD"
        req.sl = new_sl
        req.tp = new_tp
        req.comment = "Example edit sltp"
        res = simulator.order_send(req)
    print(f"Retcode: {code_text(int(res.retcode))}")

    # Example 3: Close Position
    print()
    print("=" * 70)
    print("Example 3: Close Position")
    print("=" * 70)
    if backend == "mt5":
        trade.PositionClose(ticket=pos_ticket)
        res = mt5_result(trade)
    else:
        res = simulator.close_position(pos_ticket)
    print(f"Retcode: {code_text(int(res.retcode))}")
    print(f"Deal: #{int(getattr(res, 'deal', 0))}")

    # Example 4: Placing Pending Order
    print()
    print("=" * 70)
    print("Example 4: Placing Pending Order")
    print("=" * 70)
    info = simulator.symbol_info("GBPUSD")
    if info is None:
        print("[FAIL] Failed to get GBPUSD info")
        return
    gbp_point = float(info.point)
    limit_price = float(info.ask) - (50 * gbp_point)
    sl = limit_price - (100 * gbp_point)
    tp = limit_price + (150 * gbp_point)
    if backend == "mt5":
        trade.OrderOpen("GBPUSD", mt5.ORDER_TYPE_BUY_LIMIT, 0.05, limit_price, sl, tp, comment="Example pending")
        res = mt5_result(trade)
    else:
        req = csim.TradeRequest()
        req.action = int(mt5.TRADE_ACTION_PENDING)
        req.type = int(mt5.ORDER_TYPE_BUY_LIMIT)
        req.symbol = "GBPUSD"
        req.volume = 0.05
        req.price = limit_price
        req.sl = sl
        req.tp = tp
        req.type_time = int(mt5.ORDER_TIME_GTC)
        req.comment = "Example pending"
        res = simulator.order_send(req)
    pending_ticket = int(getattr(res, "order", 0))
    print(f"Retcode: {code_text(int(res.retcode))}")
    print(f"Pending order: #{pending_ticket}")

    # Example 5: Editing Pending Order
    print()
    print("=" * 70)
    print("Example 5: Editing Pending Order")
    print("=" * 70)
    new_limit = limit_price - (10 * gbp_point)
    sl = new_limit - (100 * gbp_point)
    tp = new_limit + (150 * gbp_point)
    if backend == "mt5":
        trade.OrderModify(pending_ticket, new_limit, sl, tp)
        res = mt5_result(trade)
    else:
        req = csim.TradeRequest()
        req.action = int(mt5.TRADE_ACTION_MODIFY)
        req.order = pending_ticket
        req.price = new_limit
        req.sl = sl
        req.tp = tp
        req.comment = "Example modify pending"
        res = simulator.order_send(req)
    print(f"Retcode: {code_text(int(res.retcode))}")

    # Example 6: Deleting Pending Order
    print()
    print("=" * 70)
    print("Example 6: Deleting Pending Order")
    print("=" * 70)
    if backend == "mt5":
        trade.OrderDelete(pending_ticket)
        res = mt5_result(trade)
    else:
        req = csim.TradeRequest()
        req.action = int(mt5.TRADE_ACTION_REMOVE)
        req.order = pending_ticket
        req.comment = "Example delete pending"
        res = simulator.order_send(req)
    print(f"Retcode: {code_text(int(res.retcode))}")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
