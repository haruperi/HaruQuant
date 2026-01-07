"""
MT5 Client - Historical Data Example

This example demonstrates:
- Fetching OHLCV bars for different timeframes
- Retrieving tick data
- Getting historical orders
- Getting historical deals
- Working with date ranges
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from datetime import datetime, timedelta
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


# Initialize UserManager to get credentials
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


def example_get_bars():
    """Example: Retrieve OHLCV bars."""
    logger.info("=== Get Bars Example ===")

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
        df = client.get_bars(symbol=symbol, timeframe=timeframe, count=count)

        if not df.empty:
            logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
            logger.info(f"\nFirst 5 bars:\n{df.head()}")
            logger.info(f"\nLast bar:")
            logger.info(f"  Open: {df['open'].iloc[-1]}")
            logger.info(f"  High: {df['high'].iloc[-1]}")
            logger.info(f"  Low: {df['low'].iloc[-1]}")
            logger.info(f"  Close: {df['close'].iloc[-1]}")
            logger.info(f"  Volume: {df['volume'].iloc[-1]}")
        else:
            logger.error("Failed to retrieve bars")


def example_multiple_timeframes():
    """Example: Retrieve bars for multiple timeframes."""
    logger.info("=== Multiple Timeframes Example ===")

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
        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]

        logger.info(f"Fetching data for {symbol} across multiple timeframes:")

        for tf in timeframes:
            df = client.get_bars(symbol=symbol, timeframe=tf, count=5)
            if not df.empty:
                last_close = df['close'].iloc[-1]
                logger.info(f"  {tf}: Last Close = {last_close}")


def example_bars_date_range():
    """Example: Retrieve bars using date range."""
    logger.info("=== Bars Date Range Example ===")

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

        symbol = "GBPUSD"
        timeframe = "H1"

        # Get data for last 7 days
        date_to = datetime.now()
        date_from = date_to - timedelta(days=7)

        df = client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            date_from=date_from,
            date_to=date_to
        )

        if not df.empty:
            logger.info(f"Retrieved {len(df)} bars for {symbol} from {date_from} to {date_to}")
            logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

            # Calculate some statistics
            high_price = df['high'].max()
            low_price = df['low'].min()
            avg_volume = df['volume'].mean()

            logger.info(f"\nStatistics:")
            logger.info(f"  Highest: {high_price}")
            logger.info(f"  Lowest: {low_price}")
            logger.info(f"  Range: {high_price - low_price}")
            logger.info(f"  Avg Volume: {avg_volume:.2f}")


def example_get_ticks():
    """Example: Retrieve tick data."""
    logger.info("=== Get Ticks Example ===")

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
        count = 100  # Last 100 ticks

        # Get recent ticks as DataFrame
        df = client.get_ticks(symbol=symbol, count=count, as_dataframe=True)

        if df is not None and not df.empty:
            logger.info(f"Retrieved {len(df)} ticks for {symbol}")
            logger.info(f"\nFirst 5 ticks:\n{df.head()}")
            logger.info(f"\nLast tick:")
            logger.info(f"  Bid: {df['bid'].iloc[-1]}")
            logger.info(f"  Ask: {df['ask'].iloc[-1]}")
            logger.info(f"  Spread: {df['ask'].iloc[-1] - df['bid'].iloc[-1]}")


def example_ticks_date_range():
    """Example: Retrieve ticks using date range."""
    logger.info("=== Ticks Date Range Example ===")

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

        symbol = "USDJPY"

        # Get ticks from last hour
        end = datetime.now()
        start = end - timedelta(hours=1)

        df = client.get_ticks(symbol=symbol, start=start, end=end, as_dataframe=True)

        if df is not None and not df.empty:
            logger.info(f"Retrieved {len(df)} ticks for {symbol} in the last hour")

            # Calculate spread statistics
            spreads = df['ask'] - df['bid']
            logger.info(f"\nSpread Statistics:")
            logger.info(f"  Min Spread: {spreads.min():.5f}")
            logger.info(f"  Max Spread: {spreads.max():.5f}")
            logger.info(f"  Avg Spread: {spreads.mean():.5f}")


def example_history_orders():
    """Example: Retrieve historical orders."""
    logger.info("=== History Orders Example ===")

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

        # Get orders from last 30 days
        date_to = datetime.now()
        date_from = date_to - timedelta(days=30)

        orders = client.get_history_orders(date_from=date_from, date_to=date_to)

        if orders:
            logger.info(f"Found {len(orders)} historical orders")

            # Show first few orders
            for order in orders[:5]:
                logger.info(f"\nOrder #{order.get('ticket', 'N/A')}:")
                logger.info(f"  Symbol: {order.get('symbol', 'N/A')}")
                logger.info(f"  Type: {order.get('type', 'N/A')}")
                logger.info(f"  Volume: {order.get('volume_current', 'N/A')}")
                logger.info(f"  State: {order.get('state', 'N/A')}")
        else:
            logger.info("No historical orders found")


def example_history_deals():
    """Example: Retrieve historical deals."""
    logger.info("=== History Deals Example ===")

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

        # Get deals from last 30 days
        date_to = datetime.now()
        date_from = date_to - timedelta(days=30)

        deals = client.get_history_deals(date_from=date_from, date_to=date_to)

        if deals:
            logger.info(f"Found {len(deals)} historical deals")

            # Calculate total profit
            total_profit = sum(d.get('profit', 0) for d in deals)
            total_commission = sum(d.get('commission', 0) for d in deals)
            total_swap = sum(d.get('swap', 0) for d in deals)

            logger.info(f"\nDeal Summary:")
            logger.info(f"  Total Deals: {len(deals)}")
            logger.info(f"  Total Profit: {total_profit:.2f}")
            logger.info(f"  Total Commission: {total_commission:.2f}")
            logger.info(f"  Total Swap: {total_swap:.2f}")
            logger.info(f"  Net P&L: {total_profit + total_commission + total_swap:.2f}")

            # Show first few deals
            logger.info("\nFirst 3 deals:")
            for deal in deals[:3]:
                logger.info(f"\nDeal #{deal.get('ticket', 'N/A')}:")
                logger.info(f"  Symbol: {deal.get('symbol', 'N/A')}")
                logger.info(f"  Type: {deal.get('type', 'N/A')}")
                logger.info(f"  Volume: {deal.get('volume', 'N/A')}")
                logger.info(f"  Profit: {deal.get('profit', 'N/A')}")
        else:
            logger.info("No historical deals found")


if __name__ == "__main__":
    # Run examples
    example_get_bars()
    print("\n" + "="*60 + "\n")

    example_multiple_timeframes()
    print("\n" + "="*60 + "\n")

    example_bars_date_range()
    print("\n" + "="*60 + "\n")

    example_get_ticks()
    print("\n" + "="*60 + "\n")

    example_ticks_date_range()
    print("\n" + "="*60 + "\n")

    example_history_orders()
    print("\n" + "="*60 + "\n")

    example_history_deals()
