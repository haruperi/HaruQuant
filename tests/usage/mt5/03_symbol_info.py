"""
MT5 Client - Symbol Information Example

This example demonstrates:
- Retrieving symbol information
- Accessing symbol properties
- Working with the symbol cache
- Adding symbols to watchlist
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

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


def example_symbol_information():
    """Example: Retrieve symbol information."""
    logger.info("=== Symbol Information Example ===")

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

        # Get information for a specific symbol
        symbol = "EURUSD"
        symbol_info = client.get_symbol_info(symbol)

        if symbol_info:
            logger.info(f"Symbol Information for {symbol}:")
            logger.info(f"  Bid: {symbol_info.get('bid', 'N/A')}")
            logger.info(f"  Ask: {symbol_info.get('ask', 'N/A')}")
            logger.info(f"  Spread: {symbol_info.get('spread', 'N/A')}")
            logger.info(f"  Point: {symbol_info.get('point', 'N/A')}")
            logger.info(f"  Digits: {symbol_info.get('digits', 'N/A')}")
            logger.info(f"  Trade Mode: {symbol_info.get('trade_mode', 'N/A')}")
            logger.info(f"  Volume Min: {symbol_info.get('volume_min', 'N/A')}")
            logger.info(f"  Volume Max: {symbol_info.get('volume_max', 'N/A')}")
            logger.info(f"  Volume Step: {symbol_info.get('volume_step', 'N/A')}")
            logger.info(f"  Contract Size: {symbol_info.get('trade_contract_size', 'N/A')}")
            logger.info(f"  Swap Long: {symbol_info.get('swap_long', 'N/A')}")
            logger.info(f"  Swap Short: {symbol_info.get('swap_short', 'N/A')}")
            logger.info(f"  Description: {symbol_info.get('description', 'N/A')}")


def example_multiple_symbols():
    """Example: Retrieve information for multiple symbols."""
    logger.info("=== Multiple Symbols Example ===")

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

        # List of symbols to query
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]

        logger.info("Retrieving information for multiple symbols:")
        for symbol in symbols:
            info = client.get_symbol_info(symbol)
            if info:
                logger.info(f"{symbol}: Bid={info.get('bid', 'N/A')}, "
                          f"Ask={info.get('ask', 'N/A')}, "
                          f"Spread={info.get('spread', 'N/A')}")

        # Access cached symbol information
        logger.info("\nAccessing cached symbol data:")
        for symbol in symbols:
            if symbol in client._symbol_info_cache:
                cached = client._symbol_info_cache[symbol]
                logger.info(f"{symbol} (cached): Bid={cached.get('bid', 'N/A')}")


def example_symbol_properties():
    """Example: Access specific symbol properties."""
    logger.info("=== Symbol Properties Example ===")

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
        info = client.get_symbol_info(symbol)

        if info:
            # Calculate spread in points
            spread_points = info.get('spread', 0)
            point = info.get('point', 0)
            spread_value = spread_points * point

            logger.info(f"Trading Properties for {symbol}:")
            logger.info(f"  Current Spread: {spread_points} points ({spread_value})")
            logger.info(f"  Pip Value: {point}")
            logger.info(f"  Lot Size: {info.get('trade_contract_size', 'N/A')}")
            logger.info(f"  Min Lot: {info.get('volume_min', 'N/A')}")
            logger.info(f"  Max Lot: {info.get('volume_max', 'N/A')}")
            logger.info(f"  Lot Step: {info.get('volume_step', 'N/A')}")

            # Calculate pip value for 1 standard lot
            tick_value = info.get('trade_tick_value', 0)
            tick_size = info.get('trade_tick_size', 0)
            if tick_size > 0:
                pip_value_per_lot = tick_value / tick_size * point
                logger.info(f"  Pip Value per Lot: {pip_value_per_lot}")


def example_initial_symbols():
    """Example: Display initial symbols added to watchlist."""
    logger.info("=== Initial Symbols Example ===")

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

        logger.info(f"Total initial symbols: {len(client.initial_symbols)}")
        logger.info("Initial symbols added to watchlist:")

        # Display symbols in groups
        forex_pairs = [s for s in client.initial_symbols if len(s) == 6]
        metals = [s for s in client.initial_symbols if s.startswith('XA')]
        indices = [s for s in client.initial_symbols if s in ['US500', 'US30', 'UK100', 'GER40', 'NAS100']]
        other = [s for s in client.initial_symbols if s in ['USDX', 'EURX']]

        logger.info(f"\n  Forex Pairs ({len(forex_pairs)}): {', '.join(forex_pairs)}")
        logger.info(f"  Metals ({len(metals)}): {', '.join(metals)}")
        logger.info(f"  Indices ({len(indices)}): {', '.join(indices)}")
        logger.info(f"  Other ({len(other)}): {', '.join(other)}")


if __name__ == "__main__":
    # Run examples
    example_symbol_information()
    print("\n" + "="*60 + "\n")

    example_multiple_symbols()
    print("\n" + "="*60 + "\n")

    example_symbol_properties()
    print("\n" + "="*60 + "\n")

    example_initial_symbols()
