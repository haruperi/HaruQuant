"""
COrderInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Selecting orders by index/ticket
- Accessing order properties
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import COrderInfo
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
    logger.info("=== COrderInfo Example ===")

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
        order = COrderInfo()
        total = order.Total()
        logger.info(f"Total orders: {total}")

        if total == 0:
            logger.info("No active orders to display")
            return

        if order.SelectByIndex(0):
            logger.info(f"Ticket: {order.Ticket()}")
            logger.info(f"Symbol: {order.Symbol()}")
            logger.info(f"Type: {order.TypeDescription()}")
            logger.info(f"State: {order.StateDescription()}")
            logger.info(f"Volume: {order.VolumeCurrent()}/{order.VolumeInitial()}")
            logger.info(f"Price Open: {order.PriceOpen()}")
            logger.info(f"SL/TP: {order.StopLoss()} / {order.TakeProfit()}")
            logger.info(f"Time Setup: {order.TimeSetup()}")
            logger.info(f"Time Expiration: {order.TimeExpiration()}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
