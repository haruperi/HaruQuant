"""
CDealInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Selecting historical deals by index
- Accessing deal properties
"""

import os
import sys
from datetime import datetime, timedelta

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CDealInfo
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
    logger.info("=== CDealInfo Example ===")

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
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now()
        deal = CDealInfo(date_from=date_from, date_to=date_to)

        if not deal.SelectByIndex(0):
            logger.info("No deals found for the last 30 days")
            return

        logger.info(f"Ticket: {deal.Ticket()}")
        logger.info(f"Symbol: {deal.Symbol()}")
        logger.info(f"Type: {deal.DealTypeDescription()}")
        logger.info(f"Entry: {deal.EntryDescription()}")
        logger.info(f"Volume: {deal.Volume()}")
        logger.info(f"Price: {deal.Price()}")
        logger.info(f"Profit: {deal.Profit()}")
        logger.info(f"Commission: {deal.Commission()}")
        logger.info(f"Swap: {deal.Swap()}")
        logger.info(f"Time: {deal.Time()}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
