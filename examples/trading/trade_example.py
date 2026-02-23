"""
Basic backtest scaffold.

Step 00: initialize TradeSimulator only.
"""

import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, Trade, get_mt5_api
import hqt_engine.sim as csim
import hqt_engine
from apps.utils.logger import logger
from apps.mt5 import MT5Utils, get_mt5_api

# Global Variables
eurusd = "EURUSD"
gbpsud = "GBPUSD"
usdjpy = "USDJPY"
eurusd_ticket = 0
gbpsud_ticket = 0
usdjpy_ticket = 0
stoploss = 10
backend = "tester"  # "mt5" or "tester"

# Derived globals
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
mt5_account = client.account_info()
eurusd_info = client.symbol_info(eurusd)
account = csim.AccountInfo(mt5_account)     # Get default account info details from MT5

if backend == "mt5":
    simulator = mt5
    trade = Trade(mt5)
    trader = trade
    print("Using: MT5 backend")
else:
    simulator = csim.TradeSimulator(account)    # Initialize TradeSimulator
    simulator.set_symbol_info(eurusd_info)      # Pass MT5 symbol object metadata and seeds quotes.
    trader = simulator
    print("Using: TradeSimulator backend")

def print_example_header(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

def retcode_text(code: int) -> str:
    try:
        info = hqt_engine.error_from_retcode(int(code))
        return f"{int(code)} ({info['message']})"
    except Exception:
        return str(code)


def example_01_open_position():
    print_example_header("Example 01: Open Position")

    order_type = "SELL"
    point = float(eurusd_info.point)
    if order_type == "BUY":
        open_price = float(eurusd_info.ask)
        sl = open_price - (stoploss * point * 10)
    else:
        open_price = float(eurusd_info.bid)
        sl = open_price + (stoploss * point * 10)

    result = trader.PositionOpen(
            symbol=eurusd, 
            order_type=order_type, 
            volume=0.1, 
            price=open_price, 
            sl=sl, 
            tp=0, 
            comment="Example open position")

    if result.retcode == 10009:
        eurusd_ticket = result.order
        print(f"{eurusd} Position opened successfully with ticket number {eurusd_ticket}")
    else:
        print(f"{eurusd} Position opening failed with retcode: {retcode_text(result.retcode)}")

def example_02_modify_position():
    print_example_header("Example 02: Modify Position")
    n = 0
    while n < 10:
        for pos in simulator.positions_get():
            if pos.type == 0:  
                simulator.PositionModify(ticket=pos.ticket, sl=pos.sl - 0.005)

        time.sleep(1)
        n += 1






def main():

    if backend == "tester":
        # Set custom account info details for TradeSimulator
        account.balance = 50000.0
        account.credit = 0.0
        account.profit = 0.0
        account.equity = 50000.0
        account.margin = 0.0
        account.margin_free = 50000.0
        account.margin_level = 100.0
        account.server = "Simulator Account"
        account.company = "HaruQuant"

    if backend == "mt5":
        trade.SetExpertMagicNumber(12345)
        trade.SetDeviationInPoints(20)
        trade.SetTypeFillingBySymbol(eurusd)
        trade.SetTypeFillingBySymbol(gbpsud)



    

    example_01_open_position()
    example_02_modify_position()


    

   


    


    # Display account information
    logger.info(f"positions_total={simulator.positions_total()}")
    logger.info(f"orders_total={simulator.orders_total()}")
    logger.info(f"history_orders_total={simulator.history_orders_total()}")
    logger.info(f"history_deals_total={simulator.history_deals_total()}")


if __name__ == "__main__":
    main()
