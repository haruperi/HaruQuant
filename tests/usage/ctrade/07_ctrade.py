"""
CTrade usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Configuring CTrade parameters
- Optional trade execution (guarded by env var)
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CTrade
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
    logger.info("=== CTrade Example ===")

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
        trade = CTrade()
        trade.SetExpertMagicNumber(123456)
        trade.SetDeviationInPoints(10)
        trade.SetTypeFillingBySymbol("EURUSD")

        logger.info("Trade configured")
        logger.info(f"Configured magic: {trade.RequestMagic()}")

        execute = os.getenv("HARUQUANT_EXECUTE_TRADES", 1) == 1
        if not execute:
            logger.info("Set HARUQUANT_EXECUTE_TRADES=1 to execute real trades")
            logger.info("Set HARUQUANT_EXECUTE_PENDING=1 to place pending orders")
            return

        if trade.Buy(0.1, "EURUSD", comment="CTrade test (buy)"):
            logger.info("Buy trade executed")
            logger.info(f"Result retcode: {trade.ResultRetcodeDescription()}")
            logger.info(f"Order: {trade.ResultOrder()} Deal: {trade.ResultDeal()}")
        else:
            logger.error("Buy trade failed")
            logger.error(f"Result retcode: {trade.ResultRetcodeDescription()}")
            logger.error(f"Check retcode: {trade.CheckResultRetcodeDescription()}")
            logger.error(f"Request: {trade.Request()}")
            logger.error(f"Check: {trade.CheckResult()}")
            logger.error(f"Result: {trade.Result()}")

        if trade.Sell(0.1, "EURUSD", comment="CTrade test (sell)"):
            logger.info("Sell trade executed")
            logger.info(f"Result retcode: {trade.ResultRetcodeDescription()}")
            logger.info(f"Order: {trade.ResultOrder()} Deal: {trade.ResultDeal()}")
        else:
            logger.error("Sell trade failed")
            logger.error(f"Result retcode: {trade.ResultRetcodeDescription()}")
            logger.error(f"Check retcode: {trade.CheckResultRetcodeDescription()}")
            logger.error(f"Request: {trade.Request()}")
            logger.error(f"Check: {trade.CheckResult()}")
            logger.error(f"Result: {trade.Result()}")

        if os.getenv("HARUQUANT_EXECUTE_PENDING", 1) == 1:
            tick = mt5.symbol_info_tick("EURUSD")
            if tick is None:
                logger.error("No tick data for EURUSD; skipping pending orders")
                return

            buy_limit = tick.bid - 0.0005
            sell_limit = tick.ask + 0.0005

            if trade.BuyLimit(0.1, "EURUSD", price=buy_limit, comment="CTrade test (buy limit)"):
                logger.info("Buy Limit placed")
                logger.info(f"Order: {trade.ResultOrder()}")
            else:
                logger.error("Buy Limit failed")
                logger.error(f"Result retcode: {trade.ResultRetcodeDescription()}")

            if trade.SellLimit(0.1, "EURUSD", price=sell_limit, comment="CTrade test (sell limit)"):
                logger.info("Sell Limit placed")
                logger.info(f"Order: {trade.ResultOrder()}")
            else:
                logger.error("Sell Limit failed")
                logger.error(f"Result retcode: {trade.ResultRetcodeDescription()}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
