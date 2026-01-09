"""
MT5 Client - Advanced Usage Examples

This example demonstrates:
- Connection state management
- Error handling
- Auto-reconnection features
- Connection statistics
- Advanced patterns
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from datetime import datetime, timedelta
import time
from apps.mt5.client import MT5Client, ConnectionState
from apps.sqlite.users import UserManager
from apps.logger import logger





def example_connection_states():
    """Example: Working with connection states."""
    logger.info("=== Connection States Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    logger.info(f"Initial State: {client.connection_state}")
    logger.info(f"Is Connected: {client.is_connected()}")

    # Check state after initialization
    if client.connection_state == ConnectionState.CONNECTED:
        logger.success("Successfully connected")
    elif client.connection_state == ConnectionState.FAILED:
        logger.error("Connection failed")
    elif client.connection_state == ConnectionState.DISCONNECTED:
        logger.warning("Currently disconnected")

    # String representation
    logger.info(f"State as string: {str(client.connection_state)}")
    logger.info(f"State repr: {repr(client.connection_state)}")

    client.shutdown()
    logger.info(f"State after shutdown: {client.connection_state}")


def example_auto_reconnection():
    """Example: Enable and test auto-reconnection."""
    logger.info("=== Auto-Reconnection Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not client.is_connected():
        logger.error("Initial connection failed")
        return

    # Enable auto-reconnection
    client.auto_reconnect_enabled = True
    client.retry_attempts = 3
    client.retry_delay = 2  # seconds

    logger.info("Auto-reconnection enabled:")
    logger.info(f"  Retry Attempts: {client.retry_attempts}")
    logger.info(f"  Retry Delay: {client.retry_delay}s")

    # Simulate disconnect
    logger.info("\nSimulating disconnection...")
    client.connection_state = ConnectionState.DISCONNECTED

    # Check connection (will trigger auto-reconnect)
    logger.info("Checking connection (should trigger auto-reconnect)...")
    if client.is_connected():
        logger.success("Auto-reconnection successful!")
    else:
        logger.error("Auto-reconnection failed")

    client.shutdown()


def example_error_handling():
    """Example: Proper error handling."""
    logger.info("=== Error Handling Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    try:
        if not client.is_connected():
            raise ConnectionError("Failed to connect to MT5")

        # Try to get data for invalid symbol
        symbol = "INVALID_SYMBOL"
        logger.info(f"Attempting to get data for {symbol}...")

        symbol_info = client.get_symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"Could not retrieve info for {symbol}")

        # Try to get bars for invalid symbol
        df = client.get_bars(symbol=symbol, timeframe="H1", count=10)
        if df.empty:
            logger.warning(f"Could not retrieve bars for {symbol}")

        # Safe account info retrieval
        account_info = client.get_account_info()
        if account_info:
            logger.success("Successfully retrieved account info")
        else:
            logger.error("Failed to retrieve account info")

    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Always cleanup
        client.shutdown()
        logger.info("Cleanup completed")


def example_connection_statistics():
    """Example: Track and display connection statistics."""
    logger.info("=== Connection Statistics Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    # First connection
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    def display_stats():
        """Helper function to display statistics."""
        logger.info("Connection Statistics:")
        logger.info(f"  Total Attempts: {client._connection_attempts}")
        logger.info(f"  Successful: {client._successful_connections}")
        logger.info(f"  Failed: {client._failed_connections}")
        logger.info(f"  Last Connection: {client._last_connection_time}")
        logger.info(f"  Current State: {client.connection_state}")

    display_stats()

    # Test reconnection
    logger.info("\nTesting reconnection...")
    client.shutdown()
    time.sleep(1)
    client.reconnect()

    logger.info("\nAfter reconnection:")
    display_stats()

    # Test multiple reconnections
    logger.info("\nTesting multiple reconnections...")
    for i in range(3):
        client.shutdown()
        time.sleep(0.5)
        client.reconnect()

    logger.info("\nAfter multiple reconnections:")
    display_stats()

    client.shutdown()


def example_data_analysis():
    """Example: Analyze historical data."""
    logger.info("=== Data Analysis Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

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
        timeframe = "H1"

        # Get last 100 bars
        df = client.get_bars(symbol=symbol, timeframe=timeframe, count=100)

        if df.empty:
            logger.error("Failed to retrieve data")
            return

        # Calculate technical indicators
        df['Range'] = df['High'] - df['Low']
        df['Body'] = abs(df['Close'] - df['Open'])
        df['Upper_Shadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['Lower_Shadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']

        # Calculate statistics
        avg_range = df['Range'].mean()
        avg_volume = df['Volume'].mean()
        max_high = df['High'].max()
        min_low = df['Low'].min()

        # Price movement
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[0]
        price_change_pct = (price_change / df['Close'].iloc[0]) * 100

        logger.info(f"Analysis for {symbol} {timeframe} (Last 100 bars):")
        logger.info(f"  Period: {df.index[0]} to {df.index[-1]}")
        logger.info(f"  Current Price: {df['Close'].iloc[-1]:.5f}")
        logger.info(f"  Price Change: {price_change:.5f} ({price_change_pct:.2f}%)")
        logger.info(f"  Average Range: {avg_range:.5f}")
        logger.info(f"  Average Volume: {avg_volume:.2f}")
        logger.info(f"  High/Low: {max_high:.5f} / {min_low:.5f}")
        logger.info(f"  Total Range: {max_high - min_low:.5f}")


def example_multi_symbol_monitoring():
    """Example: Monitor multiple symbols."""
    logger.info("=== Multi-Symbol Monitoring Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    with MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ) as client:
        if not client.is_connected():
            logger.error("Failed to connect to MT5")
            return

        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]

        logger.info(f"Monitoring {len(symbols)} symbols:\n")

        for symbol in symbols:
            # Get symbol info
            info = client.get_symbol_info(symbol)

            # Get recent bars
            df = client.get_bars(symbol=symbol, timeframe="H1", count=24)

            if info and not df.empty:
                # Calculate 24h change
                change = df['Close'].iloc[-1] - df['Close'].iloc[0]
                change_pct = (change / df['Close'].iloc[0]) * 100

                # Get current prices
                bid = info.get('bid', 0)
                ask = info.get('ask', 0)
                spread = info.get('spread', 0)

                logger.info(f"{symbol}:")
                logger.info(f"  Bid/Ask: {bid:.5f} / {ask:.5f}")
                logger.info(f"  Spread: {spread} points")
                logger.info(f"  24h Change: {change:.5f} ({change_pct:+.2f}%)")
                logger.info(f"  24h High/Low: {df['High'].max():.5f} / {df['Low'].min():.5f}")
                logger.info("")


def example_client_repr():
    """Example: String representations of client."""
    logger.info("=== Client Representation Example ===")

    # Get credentials from database
    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    logger.info(f"str(client): {str(client)}")
    logger.info(f"repr(client): {repr(client)}")

    client.shutdown()


if __name__ == "__main__":
    # Run examples
    example_connection_states()
    print("\n" + "="*60 + "\n")

    example_auto_reconnection()
    print("\n" + "="*60 + "\n")

    example_error_handling()
    print("\n" + "="*60 + "\n")

    example_connection_statistics()
    print("\n" + "="*60 + "\n")

    example_data_analysis()
    print("\n" + "="*60 + "\n")

    example_multi_symbol_monitoring()
    print("\n" + "="*60 + "\n")

    example_client_repr()
