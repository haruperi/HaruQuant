"""
CAccountInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Reading account properties with CAccountInfo
- Running margin/profit helper calculations
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CAccountInfo
from apps.logger import logger
from apps.sqlite.users import UserManager


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main() -> None:
    logger.info("=== CAccountInfo Example ===")

    creds = get_mt5_credentials()

    if not mt5.initialize(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        error = mt5.last_error()
        logger.error(f"MT5 initialize failed: {error}")
        return

    try:
        account = CAccountInfo()

        logger.info(f"Login: {account.Login()}")
        logger.info(f"Name: {account.Name()}")
        logger.info(f"Server: {account.Server()}")
        logger.info(f"Company: {account.Company()}")
        logger.info(f"Currency: {account.Currency()}")
        logger.info(f"Leverage: 1:{account.Leverage()}")

        logger.info("-- Balance --")
        logger.info(f"Balance: {account.Balance():.2f}")
        logger.info(f"Equity: {account.Equity():.2f}")
        logger.info(f"Profit: {account.Profit():.2f}")
        logger.info(f"Margin: {account.Margin():.2f}")
        logger.info(f"Free Margin: {account.FreeMargin():.2f}")
        logger.info(f"Margin Level: {account.MarginLevel():.2f}")

        logger.info("-- Modes --")
        logger.info(f"Trade Mode: {account.TradeModeDescription()}")
        logger.info(f"Margin Mode: {account.MarginModeDescription()}")
        logger.info(f"Stopout Mode: {account.StopoutModeDescription()}")
        logger.info(f"Trade Allowed: {account.TradeAllowed()}")
        logger.info(f"Trade Expert: {account.TradeExpert()}")
        logger.info(f"Limit Orders: {account.LimitOrders()}")

        # Helper checks (example values)
        symbol = "EURUSD"
        order_type = mt5.ORDER_TYPE_BUY
        volume = 0.1
        price = mt5.symbol_info_tick(symbol).ask if mt5.symbol_info_tick(symbol) else 0.0

        if price:
            margin_required = account.MarginCheck(symbol, order_type, volume, price)
            free_after = account.FreeMarginCheck(symbol, order_type, volume, price)
            max_lot = account.MaxLotCheck(symbol, order_type, price, percent=50)

            logger.info("-- Checks --")
            logger.info(f"Margin Required: {margin_required:.2f}")
            logger.info(f"Free Margin After: {free_after:.2f}")
            logger.info(f"Max Lot (50% FM): {max_lot:.2f}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
