"""
CPositionInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Selecting positions by index/symbol/ticket
- Accessing position properties
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CPositionInfo
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
    logger.info("=== CPositionInfo Example ===")

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
        pos = CPositionInfo()
        total = len(mt5.positions_get() or [])
        logger.info(f"Total positions: {total}")

        if total == 0:
            logger.info("No open positions to display")
            return

        if pos.SelectByIndex(0):
            logger.info(f"Symbol: {pos.Symbol()}")
            logger.info(f"Type: {pos.TypeDescription()}")
            logger.info(f"Volume: {pos.Volume()}")
            logger.info(f"Open Price: {pos.PriceOpen()}")
            logger.info(f"Current Price: {pos.PriceCurrent()}")
            logger.info(f"SL/TP: {pos.StopLoss()} / {pos.TakeProfit()}")
            logger.info(f"Profit: {pos.Profit()}")
            logger.info(f"Time Open: {pos.Time()}")

            pos.StoreState()
            logger.info(f"State Stored: {pos.CheckState()}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
