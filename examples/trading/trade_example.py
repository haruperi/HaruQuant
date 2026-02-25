"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys

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
backend = "tester"  # "mt5" or "tester"

# Derived globals
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
mt5_account = client.account_info()
test_symbol_info = client.symbol_info(test_symbol)
_simulator = None
_account = None

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

def _calc_profit(calc_api, symbol: str, volume: float, entry_price: float, exit_price: float):
    return calc_api.order_calc_profit(0, symbol, volume, entry_price, exit_price)

def _calc_margin(calc_api, symbol: str, volume: float, entry_price: float):
    return calc_api.order_calc_margin(0, symbol, volume, entry_price)


def example_01_open_position():
    print_example_header("Example 01: Open Position")
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

    symbol_store = core.SymbolInfo(_account)
    for sym in ordered_symbols:
        info = client.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)
        exit_price = entry_price + (265 * float(info.point))

        symbol_store.AddSymbol(info)
        mt5_profit = _calc_profit(mt5, sym, volume, entry_price, exit_price)
        tester_profit = _calc_profit(_simulator, sym, volume, entry_price, exit_price)
        print(f"{sym}: MT5=${mt5_profit} | Tester=${tester_profit}")

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

    symbol_store = core.SymbolInfo(_account)
    for sym in ordered_symbols:
        info = client.symbol_info(sym)
        if info is None:
            print(f"{sym}: symbol info unavailable, skipped")
            continue

        entry_price = float(info.ask)

        symbol_store.AddSymbol(info)
        mt5_margin = _calc_margin(mt5, sym, volume, entry_price)
        tester_margin = _calc_margin(_simulator, sym, volume, entry_price)
        print(f"{sym}: MT5=${mt5_margin} | Tester=${tester_margin}")


if __name__ == "__main__":
    example_01_open_position()
    example_02_calculate_profit()
    example_03_calculate_margin()

    client.shutdown()
