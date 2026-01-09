"""
MT5 Client - Positions and Orders Example

This example demonstrates:
- Retrieving open positions
- Retrieving active orders
- Filtering positions and orders
- Displaying position/order details
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger





def example_get_positions():
    """Example: Retrieve all open positions."""
    logger.info("=== Get Positions Example ===")

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

        # Get all positions
        positions = client.get_positions()

        if positions:
            logger.info(f"Found {len(positions)} open position(s)")

            for pos in positions:
                logger.info(f"\nPosition #{pos.get('ticket', 'N/A')}:")
                logger.info(f"  Symbol: {pos.get('symbol', 'N/A')}")
                logger.info(f"  Type: {'BUY' if pos.get('type') == 0 else 'SELL'}")
                logger.info(f"  Volume: {pos.get('volume', 'N/A')}")
                logger.info(f"  Open Price: {pos.get('price_open', 'N/A')}")
                logger.info(f"  Current Price: {pos.get('price_current', 'N/A')}")
                logger.info(f"  Profit: {pos.get('profit', 'N/A')}")
                logger.info(f"  SL: {pos.get('sl', 'N/A')}")
                logger.info(f"  TP: {pos.get('tp', 'N/A')}")
                logger.info(f"  Comment: {pos.get('comment', 'N/A')}")
        else:
            logger.info("No open positions found")


def example_filter_positions():
    """Example: Filter positions by symbol."""
    logger.info("=== Filter Positions Example ===")

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

        # Filter positions by symbol
        symbol = "EURUSD"
        positions = client.get_positions(symbol=symbol)

        if positions:
            logger.info(f"Found {len(positions)} position(s) for {symbol}")

            total_volume = sum(p.get('volume', 0) for p in positions)
            total_profit = sum(p.get('profit', 0) for p in positions)

            logger.info(f"Total Volume: {total_volume}")
            logger.info(f"Total Profit: {total_profit}")
        else:
            logger.info(f"No open positions found for {symbol}")


def example_get_orders():
    """Example: Retrieve all active orders."""
    logger.info("=== Get Orders Example ===")

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

        # Get all orders
        orders = client.get_orders()

        if orders:
            logger.info(f"Found {len(orders)} active order(s)")

            for order in orders:
                logger.info(f"\nOrder #{order.get('ticket', 'N/A')}:")
                logger.info(f"  Symbol: {order.get('symbol', 'N/A')}")
                logger.info(f"  Type: {order.get('type', 'N/A')}")
                logger.info(f"  Volume: {order.get('volume_current', 'N/A')}")
                logger.info(f"  Price Open: {order.get('price_open', 'N/A')}")
                logger.info(f"  SL: {order.get('sl', 'N/A')}")
                logger.info(f"  TP: {order.get('tp', 'N/A')}")
                logger.info(f"  State: {order.get('state', 'N/A')}")
                logger.info(f"  Comment: {order.get('comment', 'N/A')}")
        else:
            logger.info("No active orders found")


def example_position_summary():
    """Example: Calculate position summary statistics."""
    logger.info("=== Position Summary Example ===")

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

        positions = client.get_positions()

        if not positions:
            logger.info("No positions to summarize")
            return

        # Calculate summary statistics
        total_positions = len(positions)
        buy_positions = sum(1 for p in positions if p.get('type') == 0)
        sell_positions = sum(1 for p in positions if p.get('type') == 1)
        total_profit = sum(p.get('profit', 0) for p in positions)
        total_volume = sum(p.get('volume', 0) for p in positions)

        # Group by symbol
        symbol_summary = {}
        for pos in positions:
            symbol = pos.get('symbol', 'Unknown')
            if symbol not in symbol_summary:
                symbol_summary[symbol] = {
                    'count': 0,
                    'volume': 0,
                    'profit': 0
                }
            symbol_summary[symbol]['count'] += 1
            symbol_summary[symbol]['volume'] += pos.get('volume', 0)
            symbol_summary[symbol]['profit'] += pos.get('profit', 0)

        # Display summary
        logger.info("Position Summary:")
        logger.info(f"  Total Positions: {total_positions}")
        logger.info(f"  Buy Positions: {buy_positions}")
        logger.info(f"  Sell Positions: {sell_positions}")
        logger.info(f"  Total Profit: {total_profit:.2f}")
        logger.info(f"  Total Volume: {total_volume:.2f}")

        logger.info("\nBreakdown by Symbol:")
        for symbol, data in symbol_summary.items():
            logger.info(f"  {symbol}:")
            logger.info(f"    Count: {data['count']}")
            logger.info(f"    Volume: {data['volume']:.2f}")
            logger.info(f"    Profit: {data['profit']:.2f}")


def example_specific_position():
    """Example: Get specific position by ticket."""
    logger.info("=== Specific Position Example ===")

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

        # First get all positions to find a ticket
        all_positions = client.get_positions()

        if not all_positions:
            logger.info("No positions available to query")
            return

        # Get first position ticket
        ticket = all_positions[0].get('ticket')
        logger.info(f"Querying position with ticket: {ticket}")

        # Get specific position
        position = client.get_positions(ticket=ticket)

        if position:
            pos = position[0]
            logger.info(f"\nPosition Details:")
            logger.info(f"  Ticket: {pos.get('ticket', 'N/A')}")
            logger.info(f"  Symbol: {pos.get('symbol', 'N/A')}")
            logger.info(f"  Type: {'BUY' if pos.get('type') == 0 else 'SELL'}")
            logger.info(f"  Volume: {pos.get('volume', 'N/A')}")
            logger.info(f"  Price Open: {pos.get('price_open', 'N/A')}")
            logger.info(f"  Current Price: {pos.get('price_current', 'N/A')}")
            logger.info(f"  Profit: {pos.get('profit', 'N/A')}")
            logger.info(f"  Swap: {pos.get('swap', 'N/A')}")
            logger.info(f"  Magic: {pos.get('magic', 'N/A')}")


if __name__ == "__main__":
    # Run examples
    example_get_positions()
    print("\n" + "="*60 + "\n")

    example_filter_positions()
    print("\n" + "="*60 + "\n")

    example_get_orders()
    print("\n" + "="*60 + "\n")

    example_position_summary()
    print("\n" + "="*60 + "\n")

    example_specific_position()
