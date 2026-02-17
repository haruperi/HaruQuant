"""Basic usage examples for indicator functions."""

import pandas as pd
from datetime import datetime
from apps.indicator import accumulation_distribution, atr, ema, rsi, sma, wma
from apps.utils.logger import logger
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
import sys

def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main() -> None:
    """Run indicator calculations and print resulting columns."""

   # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not connected:
        logger.error("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    symbol = "EURUSD"
    timeframe = "H1"  # 1-hour bars
    count = 10  # Last 10 bars

    # Get bars
    data = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=datetime(2025, 1, 1), date_to=datetime(2025, 12, 31))

    logger.info("Calculating indicators")
    data = rsi(data, period=3)
    data = sma(data, window=3)
    data = ema(data, span=3)
    data = wma(data, window=3)
    data = atr(data, period=3)
    data = accumulation_distribution(data)

    logger.success("Indicators calculated; previewing result")
    print(data.tail())

if __name__ == "__main__":
    main()

