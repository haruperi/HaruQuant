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

import hqt_engine.sim as csim
from apps.utils.logger import logger
from apps.mt5 import MT5Utils, get_mt5_api

eurusd = "EURUSD"
gbpsud = "GBPUSD"
usdjpy = "USDJPY"


def main():
    # Get default account info details from MT5
    client = MT5Utils.get_connected_client()
    mt5_account = client.account_info()
    eurusd_info = client.symbol_info(eurusd)

    # Set custom account info details for TradeSimulator
    account = csim.AccountInfo(mt5_account)
    account.balance = 50000.0
    account.credit = 0.0
    account.profit = 0.0
    account.equity = 50000.0
    account.margin = 0.0
    account.margin_free = 50000.0
    account.margin_level = 100.0
    account.server = "Simulator Account"
    account.company = "HaruQuant"

    # Initialize TradeSimulator
    simulator = csim.TradeSimulator(account)

    # Pass MT5 symbol object directly; backend maps metadata and seeds quotes.
    simulator.set_symbol_info(eurusd_info)

    # Trading 
    stoploss = 10

    simulator.PositionOpen(
        symbol=eurusd, 
        order_type="BUY", 
        volume=0.1, 
        price=eurusd_info.ask, 
        sl=eurusd_info.bid - stoploss*eurusd_info.point*10, 
        tp=0, 
        comment="Example open position")


    n = 0
    while n < 10:
        for pos in simulator.positions_get():
            if pos.type == "BUY":  
                simulator.PositionModify(ticket=pos.ticket, sl=pos.sl - 0.005)

        time.sleep(1)
        n += 1


    # Display account information
    logger.info(f"positions_total={simulator.positions_total()}")
    logger.info(f"orders_total={simulator.orders_total()}")
    logger.info(f"history_orders_total={simulator.history_orders_total()}")
    logger.info(f"history_deals_total={simulator.history_deals_total()}")


if __name__ == "__main__":
    main()
