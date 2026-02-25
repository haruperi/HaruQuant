"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

import haruquant
import haruquant.core as core
from apps.mt5 import MT5Utils, Trade as LiveTrade, get_mt5_api

# Global Variables
test_symbol = "NZDCAD"
audusd = "AUDUSD"
eurgbp = "EURGBP"
usdjpy = "USDJPY"
stoploss = 10
backend = "mt5"  # "mt5" or "tester"

# Derived globals
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
mt5_account = client.account_info()
test_symbol_info = client.symbol_info(test_symbol)
_simulator = None
_account = None
pending_orders_created = []

if backend == "mt5":
        trade = LiveTrade(mt5)
        print("Using: MT5 backend")
else:
        _account = core.AccountInfo(mt5_account)
        _account.SetBalance(50000.0)
        _account.SetEquity(50000.0)
        _account.SetMargin(0.0)
        _account.SetMarginFree(50000.0)
        _account.SetServer("Simulator Account")
        _account.SetCompany("HaruQuant")

        _simulator = core.BacktestSimulator(_account)
        trade = core.Trade(_account)
        print("Using: Tester backend")

trade.SetExpertMagicNumber(12345)
trade.SetDeviationInPoints(20)
trade.SetTypeFillingBySymbol(test_symbol)

def print_example_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def example_01_open_position():
    print_example_header("Example 01: Open Position")
    order_type = "BUY"
    point = float(test_symbol_info.point)
    open_price = float(test_symbol_info.bid) if order_type == "SELL" else float(test_symbol_info.ask)
    sl = open_price + (stoploss * point * 10) if order_type == "SELL" else open_price - (stoploss * point * 10)

    if backend == "tester":
        symbol_store = core.SymbolInfo(_account)
        symbol_store.AddSymbol(test_symbol_info)

    result = trade.PositionOpen(
            symbol=test_symbol,
            order_type=order_type,
            volume=0.01,
            price=open_price,
            sl=sl,
            tp=0.0,
            comment="Example open position",
        )
    if int(result.retcode) == 10009:
        print(f"{test_symbol} Position opened successfully with ticket {int(result.order)}")
    else:
        desc = str(trade.ResultRetcodeDescription())
        suffix = f"; {desc}" if desc and desc != str(int(result.retcode)) else ""
        print(
            f"{test_symbol} Position opening failed with retcode "
            f"retcode {int(result.retcode)}, {suffix}"
        )

    

def example_02_calculate_profit():
    print_example_header("Example 02: Calculate Profit")
    volume = 0.10
    symbols_to_test = [audusd, usdjpy, eurgbp, test_symbol]
    ordered_symbols = []
    seen = set()
    for sym in symbols_to_test:
        if sym not in seen:
            seen.add(sym)
            ordered_symbols.append(sym)

    for sym in ordered_symbols:
        info = client.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)
        exit_price = entry_price + (265 * float(info.point))
        mt5_profit = mt5.order_calc_profit(0, sym, volume, entry_price, exit_price)
        if backend == "tester":
            symbol_store = core.SymbolInfo(_account)
            symbol_store.AddSymbol(info)
            tester_profit = _simulator.order_calc_profit(0, sym, volume, entry_price, exit_price)
            print(f"{sym}: MT5=${mt5_profit} | Tester=${tester_profit}")
        else:
            print(f"{sym}: MT5=${mt5_profit}")

def example_03_calculate_margin():
    print_example_header("Example 03: Calculate Margin")
    volume = 0.10
    symbols_to_test = [audusd, usdjpy, eurgbp, test_symbol]
    ordered_symbols = []
    seen = set()
    for sym in symbols_to_test:
        if sym not in seen:
            seen.add(sym)
            ordered_symbols.append(sym)

    for sym in ordered_symbols:
        info = client.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)
        mt5_margin = mt5.order_calc_margin(0, sym, volume, entry_price)
        if backend == "tester":
            symbol_store = core.SymbolInfo(_account)
            symbol_store.AddSymbol(info)
            tester_margin = _simulator.order_calc_margin(0, sym, volume, entry_price)
            print(f"{sym}: MT5=${mt5_margin} | Tester=${tester_margin}")
        else:
            print(f"{sym}: MT5=${mt5_margin}")

def example_04_modify_position():
    print_example_header("Example 04: Modify Position (SL/TP)")
    info = client.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    point = float(info.point)
    bid = float(info.bid)
    ask = float(info.ask)
    new_sl = bid - (30 * point * 10)
    new_tp = ask + (30 * point * 10)

    if backend == "mt5":
        result = trade.PositionModify(symbol=test_symbol, sl=new_sl, tp=new_tp)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{test_symbol} Position modified successfully")
        else:
            print(
                f"{test_symbol} Position modify failed with retcode "
                f"{int(result.retcode)}"
            )
    else:
        ok = trade.PositionModify(symbol=test_symbol, sl=new_sl, tp=new_tp)
        retcode = int(trade.ResultRetcode())
        if ok and retcode == 10009:
            print(f"{test_symbol} Position modified successfully")
        else:
            desc = str(trade.ResultRetcodeDescription())
            suffix = f"; {desc}" if desc and desc != str(retcode) else ""
            print(
                f"{test_symbol} Position modify failed with retcode "
                f"{retcode}{suffix}"
            )

def example_05_close_partial_position():
    print_example_header("Example 06: Close Partial Position")
    info = client.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    if backend == "tester":
        symbol_store = core.SymbolInfo(_account)
        symbol_store.AddSymbol(info)

    open_price = float(info.ask)
    open_result = trade.PositionOpen(
        symbol=test_symbol,
        order_type="BUY",
        volume=0.02,
        price=open_price,
        sl=0.0,
        tp=0.0,
        comment="Example partial close seed",
    )

    if backend == "mt5":
        if not open_result or int(open_result.retcode) not in (10008, 10009):
            print(f"{test_symbol}: seed position failed, partial close skipped")
            return
        result = trade.PositionClosePartial(symbol=test_symbol, volume=0.01)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{test_symbol} Position partially closed successfully")
        else:
            print(
                f"{test_symbol} Partial close failed with retcode "
                f"{int(result.retcode)}"
            )
    else:
        if not open_result or int(trade.ResultRetcode()) != 10009:
            print(f"{test_symbol}: seed position failed, partial close skipped")
            return
        ok = trade.PositionClosePartial(symbol=test_symbol, volume=0.01)
        retcode = int(trade.ResultRetcode())
        if ok and retcode == 10009:
            print(f"{test_symbol} Position partially closed successfully")
        else:
            desc = str(trade.ResultRetcodeDescription())
            suffix = f"; {desc}" if desc and desc != str(retcode) else ""
            print(
                f"{test_symbol} Partial close failed with retcode "
                f"{retcode}{suffix}"
            )


def example_06_close_position():
    print_example_header("Example 05: Close Position")
    if backend == "mt5":
        result = trade.PositionClose(symbol=test_symbol)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{test_symbol} Position closed successfully")
        else:
            print(
                f"{test_symbol} Position close failed with retcode "
                f"{int(result.retcode)}"
            )
    else:
        ok = trade.PositionClose(symbol=test_symbol)
        retcode = int(trade.ResultRetcode())
        if ok and retcode == 10009:
            print(f"{test_symbol} Position closed successfully")
        else:
            desc = str(trade.ResultRetcodeDescription())
            suffix = f"; {desc}" if desc and desc != str(retcode) else ""
            print(
                f"{test_symbol} Position close failed with retcode "
                f"{retcode}{suffix}"
            )

def example_07_pending_orders():
    print_example_header("Example 07: Pending Orders (4 Types)")
    pending_orders_created.clear()
    info = client.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    if backend == "tester":
        symbol_store = core.SymbolInfo(_account)
        symbol_store.AddSymbol(info)

    bid = float(info.bid)
    ask = float(info.ask)
    point = float(info.point)
    step = 25 * point * 10
    expiration = int(time.time()) + 3600
    volume = 0.01

    pending_specs = [
        ("BUY_LIMIT", ask - step),
        ("BUY_STOP", ask + step),
        ("SELL_LIMIT", bid + step),
        ("SELL_STOP", bid - step),
    ]

    for order_type, pending_price in pending_specs:
        if backend == "mt5":
            result = trade.OrderOpen(
                symbol=test_symbol,
                order_type=order_type,
                volume=volume,
                price=pending_price,
                sl=0.0,
                tp=0.0,
                expiration=datetime.fromtimestamp(expiration),
                comment=f"Example {order_type}",
            )
            if result and int(result.retcode) in (10008, 10009):
                ticket = int(result.order)
                pending_orders_created.append((ticket, order_type))
                print(f"{order_type}: placed successfully (order={ticket})")
            else:
                print(f"{order_type}: failed retcode={int(result.retcode)}")
        else:
            ok = trade.OrderOpen(
                symbol=test_symbol,
                order_type=order_type,
                volume=volume,
                limit_price=pending_price,
                price=0.0,
                sl=0.0,
                tp=0.0,
                expiration=expiration,
                comment=f"Example {order_type}",
            )
            retcode = int(trade.ResultRetcode())
            if ok and retcode in (10008, 10009):
                ticket = int(trade.ResultOrder())
                pending_orders_created.append((ticket, order_type))
                print(f"{order_type}: placed successfully (order={ticket})")
            else:
                desc = str(trade.ResultRetcodeDescription())
                suffix = f"; {desc}" if desc and desc != str(retcode) else ""
                print(f"{order_type}: failed retcode={retcode}{suffix}")

def example_08_modify_pending_orders():
    print_example_header("Example 08: Modify Pending Orders")
    if not pending_orders_created:
        print("No pending orders available to modify")
        return

    info = client.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

    bid = float(info.bid)
    ask = float(info.ask)
    point = float(info.point)
    step = 30 * point * 10
    expiration = int(time.time()) + 7200

    for ticket, order_type in pending_orders_created:
        if order_type == "BUY_LIMIT":
            new_price = ask - step
        elif order_type == "BUY_STOP":
            new_price = ask + step
        elif order_type == "SELL_LIMIT":
            new_price = bid + step
        else:
            new_price = bid - step

        if backend == "mt5":
            result = trade.OrderModify(
                ticket=ticket,
                price=new_price,
                sl=0.0,
                tp=0.0,
                expiration=datetime.fromtimestamp(expiration),
            )
            if result and int(result.retcode) in (10008, 10009):
                print(f"{order_type} ticket {ticket}: modified")
            else:
                print(f"{order_type} ticket {ticket}: modify failed retcode={int(result.retcode)}")
        else:
            ok = trade.OrderModify(
                ticket=ticket,
                price=new_price,
                sl=0.0,
                tp=0.0,
                type_time=0,
                expiration=expiration,
                stoplimit_price=0.0,
            )
            retcode = int(trade.ResultRetcode())
            if ok and retcode in (10008, 10009):
                print(f"{order_type} ticket {ticket}: modified")
            else:
                desc = str(trade.ResultRetcodeDescription())
                suffix = f"; {desc}" if desc and desc != str(retcode) else ""
                print(f"{order_type} ticket {ticket}: modify failed retcode={retcode}{suffix}")


if __name__ == "__main__":
    example_01_open_position()
    example_02_calculate_profit()
    example_03_calculate_margin()
    example_04_modify_position()
    example_05_close_partial_position()
    example_06_close_position()
    example_07_pending_orders()
    time.sleep(2)
    example_08_modify_pending_orders()
    

    client.shutdown()
