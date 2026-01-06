"""Basic usage examples for indicator functions."""

import pandas as pd
from datetime import datetime
from apps.indicator import accumulation_distribution, atr, ema, rsi, sma, wma
from apps.logger import logger
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager

def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"  # Change this to your username
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        sys.exit(1)

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        sys.exit(1)

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")
    return creds


def main() -> None:
    """Run indicator calculations and print resulting columns."""

    # Get credentials from database
    creds = get_mt5_credentials()
    
    with MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ) as client:
        if not client.is_connected():
            logger.error("Failed to connect to MT5")
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
