"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.utils.logger import logger
from apps.trading import Engine, core, Trade


# Global Variables
test_symbol = "NZDCAD"
audusd = "AUDUSD"
eurgbp = "EURGBP"
usdjpy = "USDJPY"
stoploss = 10

# Derived globals
backend = "mt5"  # set to: "mt5" or "sim"
engine_instance = Engine(backend=backend)
api = engine_instance.api
account = api.account_info()

if backend == "sim":
    # Override selected MT5-derived fields for tester backend.
    account['login'] = 123456
    account['server'] = "Backtest Simulation Server"
    account['company'] = "HaruQuant"
    account['balance'] = 10000.0
    account['credit'] = 0.0
    account['profit'] = 0.0
    account['equity'] = 10000.0
    account['margin'] = 0.0
    account['margin_free'] = 10000.0

    mt5_test_symbol_info = engine_instance.client.symbol_info(test_symbol)
    mt5_audusd_symbol_info = engine_instance.client.symbol_info(audusd)
    mt5_eurgbp_symbol_info = engine_instance.client.symbol_info(eurgbp)
    mt5_usdjpy_symbol_info = engine_instance.client.symbol_info(usdjpy)
    engine_instance.state.trading_symbols.append(mt5_test_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_audusd_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_eurgbp_symbol_info)
    engine_instance.state.trading_symbols.append(mt5_usdjpy_symbol_info)
    print("Using: Tester backend")

else:
    print("Using: MT5 backend")


trade = Trade(api)
trade.SetExpertMagicNumber(12345)
trade.SetDeviationInPoints(20)
trade.SetTypeFillingBySymbol(test_symbol)
pending_orders_created = []

def print_example_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def example_01_open_position():
    print_example_header("Example 01: Open Position")
    test_symbol_info = api.symbol_info(test_symbol)
    order_type = "BUY"
    point = float(test_symbol_info.point)
    open_price = float(test_symbol_info.bid) if order_type == "SELL" else float(test_symbol_info.ask)
    sl = open_price + (stoploss * point * 10) if order_type == "SELL" else open_price - (stoploss * point * 10)

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


def example_02_calculate_profit_margin():
    print_example_header("Example 02: Calculate Profit and Margin")
    volume = 0.10
    symbols_to_test = [audusd, usdjpy, eurgbp, test_symbol]
    ordered_symbols = []
    seen = set()
    for sym in symbols_to_test:
        if sym not in seen:
            seen.add(sym)
            ordered_symbols.append(sym)

    for sym in ordered_symbols:
        info = api.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)
        exit_price = entry_price + (265 * float(info.point))
        mt5_profit = engine_instance.client.order_calc_profit(0, sym, volume, entry_price, exit_price)
        mt5_margin = engine_instance.client.order_calc_margin(0, sym, volume, entry_price)

        # if backend == "tester":
        #     symbol_store = core.SymbolInfo(_account)
        #     symbol_store.AddSymbol(info)
        #     tester_profit = _simulator.order_calc_profit(0, sym, volume, entry_price, exit_price)
        #     tester_margin = _simulator.order_calc_margin(0, sym, volume, entry_price)
        #     print(f"{sym}: MT5=${mt5_profit} | Tester=${tester_profit}")
        # else:
        #     print(f"{sym}: MT5=${mt5_profit}")

        print(f"{sym}: MT5 profit = {mt5_profit}, margin = {mt5_margin}")


def example_03_modify_position():
    print_example_header("Example 03: Modify Position (SL/TP)")
    info = api.symbol_info(test_symbol)
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


def example_04_close_partial_position():
    print_example_header("Example 04: Close Partial Position")
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

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


def example_05_close_position():
    print_example_header("Example 05: Close Position")
    result = trade.PositionClose(symbol=test_symbol)
    if result and int(result.retcode) in (10008, 10009):
        print(f"{test_symbol} Position closed successfully")
    else:
        print(
            f"{test_symbol} Position close failed with retcode "
            f"{int(result.retcode)}"
        )


def example_06_pending_orders():
    print_example_header("Example 06: Pending Orders (4 Types)")
    pending_orders_created.clear()
    info = api.symbol_info(test_symbol)
    if info is None:
        print(f"{test_symbol}: symbol info unavailable, skipped")
        return

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


def example_07_modify_pending_orders():
    print_example_header("Example 07: Modify Pending Orders")
    if not pending_orders_created:
        print("No pending orders available to modify")
        return

    info = api.symbol_info(test_symbol)
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


def example_08_delete_pending_orders():
    print_example_header("Example 08: Delete Pending Orders")
    if not pending_orders_created:
        print("No pending orders available to delete")
        return

    remaining = []
    for ticket, order_type in pending_orders_created:
        result = trade.OrderDelete(ticket=ticket)
        if result and int(result.retcode) in (10008, 10009):
            print(f"{order_type} ticket {ticket}: deleted")
        else:
            print(f"{order_type} ticket {ticket}: delete failed retcode={int(result.retcode)}")
            remaining.append((ticket, order_type))

    pending_orders_created.clear()
    pending_orders_created.extend(remaining)


if __name__ == "__main__":
    example_01_open_position()
    example_02_calculate_profit_margin()
    example_03_modify_position()
    example_04_close_partial_position()
    example_05_close_position()
    example_06_pending_orders()
    example_07_modify_pending_orders()
    example_08_delete_pending_orders()

    

    if 'engine_instance' in locals():
            print("\nShutting down MT5 connection...")
            engine_instance.client.shutdown()
            print("Disconnected.")
