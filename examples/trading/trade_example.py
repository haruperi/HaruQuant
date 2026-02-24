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
eurusd = "EURUSD"
gbpsud = "GBPUSD"
usdjpy = "USDJPY"
stoploss = 10
backend = "mt5"  # "mt5" or "tester"

# Derived globals
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
mt5_account = client.account_info()
eurusd_info = client.symbol_info(eurusd)

if backend == "mt5":
        trade = LiveTrade(mt5)
        print("Using: MT5 backend")
else:
        account = core.AccountInfo(mt5_account)
        account.SetBalance(50000.0)
        account.SetEquity(50000.0)
        account.SetMargin(0.0)
        account.SetMarginFree(50000.0)
        account.SetServer("Simulator Account")
        account.SetCompany("HaruQuant")

        _simulator = core.BacktestSimulator(account)
        trade = core.Trade(account)
        print("Using: Tester backend")

trade.SetExpertMagicNumber(12345)
trade.SetDeviationInPoints(20)
trade.SetTypeFillingBySymbol(eurusd)

def print_example_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)



def example_01_open_position():
    print_example_header("Example 01: Open Position")
    order_type = "BUY"
    point = float(eurusd_info.point)
    open_price = float(eurusd_info.bid) if order_type == "SELL" else float(eurusd_info.ask)
    sl = open_price + (stoploss * point * 10) if order_type == "SELL" else open_price - (stoploss * point * 10)

    result = trade.PositionOpen(
            symbol=eurusd,
            order_type=order_type,
            volume=0.01,
            price=open_price,
            sl=sl,
            tp=0.0,
            comment="Example open position",
        )
    if int(result.retcode) == 10009:
        print(f"{eurusd} Position opened successfully with ticket {int(result.order)}")
    else:
        desc = str(trade.ResultRetcodeDescription())
        suffix = f"; {desc}" if desc and desc != str(int(result.retcode)) else ""
        print(
            f"{eurusd} Position opening failed with retcode "
            f"retcode {int(result.retcode)}, {suffix}"
        )

    client.shutdown()


if __name__ == "__main__":
    example_01_open_position()

