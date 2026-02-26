"""Example usage of Trade with MT5/Tester backend parity."""


import os
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.utils.logger import logger
from apps.trading import Engine, core, Trade

# Mocking test symbols and imports missing from example
from apps.mt5 import MT5Utils, get_mt5_api
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
test_symbol_info = mt5.symbol_info("NZDCAD") if mt5 else None

# Global Variables
test_symbol = "NZDCAD"
audusd = "AUDUSD"
eurgbp = "EURGBP"
usdjpy = "USDJPY"
stoploss = 10
backend = "mt5"  # "mt5" or "tester"

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
if backend == "mt5":
    trade = Trade(api)
    print("Using: MT5 backend")
else:
    # Hydrate simulator with test variables
    if test_symbol_info:
        api.state.trading_symbols.append(test_symbol_info)
    trade = Trade(api)
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
        symbol_store = main.SymbolInfo(_account)
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




if __name__ == "__main__":
    example_01_open_position()

    

    client.shutdown()
