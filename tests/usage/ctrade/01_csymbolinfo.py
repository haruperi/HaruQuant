"""
CSymbolInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Refreshing symbol data and tick data
- Accessing grouped CSymbolInfo properties
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CSymbolInfo
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
    logger.info("=== CSymbolInfo Example ===")

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
        symbol_name = "EURUSD"
        symbol = CSymbolInfo(symbol_name)

        if not symbol.Refresh():
            logger.error(f"Failed to refresh symbol data for {symbol_name}")
            return

        if not symbol.RefreshRates():
            logger.error(f"Failed to refresh tick data for {symbol_name}")
            return

        logger.info(f"Symbol: {symbol.Name()}")
        logger.info(f"Time: {symbol.Time()}")
        logger.info(f"Bid/Ask: {symbol.Bid()} / {symbol.Ask()}")
        logger.info(f"Spread: {symbol.Spread()} points")
        logger.info(f"Digits/Point: {symbol.Digits()} / {symbol.Point()}")

        logger.info("-- Volumes --")
        logger.info(f"Volume: {symbol.Volume()}")
        logger.info(f"Volume High: {symbol.VolumeHigh()}")
        logger.info(f"Volume Low: {symbol.VolumeLow()}")

        logger.info("-- Trade modes --")
        logger.info(f"Trade Mode: {symbol.TradeModeDescription()}")
        logger.info(f"Execution: {symbol.TradeExecutionDescription()}")
        logger.info(f"Calc Mode: {symbol.TradeCalcModeDescription()}")

        logger.info("-- Contracts & Swaps --")
        logger.info(f"Contract Size: {symbol.ContractSize()}")
        logger.info(f"Lots Min/Max/Step: {symbol.LotsMin()} / {symbol.LotsMax()} / {symbol.LotsStep()}")
        logger.info(f"Swap Mode: {symbol.SwapModeDescription()}")
        logger.info(f"Swap Long/Short: {symbol.SwapLong()} / {symbol.SwapShort()}")

        logger.info("-- Text properties --")
        logger.info(f"Description: {symbol.Description()}")
        logger.info(f"Path: {symbol.Path()}")
        logger.info(f"Base/Profit/Margin: {symbol.CurrencyBase()} / {symbol.CurrencyProfit()} / {symbol.CurrencyMargin()}")

        logger.info("-- Service --")
        test_price = 1.105678
        logger.info(f"NormalizePrice({test_price}) -> {symbol.NormalizePrice(test_price)}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
