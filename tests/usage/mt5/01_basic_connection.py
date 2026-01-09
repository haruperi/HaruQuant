"""
MT5 Client - Basic Connection Example

This example demonstrates:
- Basic initialization and connection to MT5
- Checking connection status
- Proper shutdown
- Using context manager
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger


def example_basic_connection():
    """Example: Basic connection and shutdown."""
    logger.info("=== Basic Connection Example ===")

    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)

    # Create client with credentials
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
        timeout=60000,  # 60 seconds timeout
        portable=False
    )

    # Check if connected
    if client.is_connected():
        logger.success("Successfully connected to MT5!")

        # Get account info
        account_info = client.get_account_info()
        if account_info:
            logger.info(f"Account Balance: {account_info.get('balance', 'N/A')}")
            logger.info(f"Account Currency: {account_info.get('currency', 'N/A')}")
            logger.info(f"Account Leverage: 1:{account_info.get('leverage', 'N/A')}")
    else:
        logger.error("Failed to connect to MT5")

    # Clean shutdown
    client.shutdown()
    logger.info("Connection closed")


def example_context_manager():
    """Example: Using context manager for automatic cleanup."""
    logger.info("=== Context Manager Example ===")

    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        return

    # Context manager ensures shutdown is called even if exception occurs
    with MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ) as client:
        if client.is_connected():
            logger.success("Connected using context manager")

            # Do your work here
            terminal_info = client.get_terminal_info()
            if terminal_info:
                logger.info(f"Terminal Build: {terminal_info.get('build', 'N/A')}")
                logger.info(f"Terminal Company: {terminal_info.get('company', 'N/A')}")
        else:
            logger.error("Connection failed")

    # Shutdown is automatically called when exiting the context
    logger.info("Context manager automatically closed connection")


def example_reconnection():
    """Example: Manual reconnection."""
    logger.info("=== Reconnection Example ===")

    # Get credentials from database
    creds = UserManager().get_mt5_credentials()
    if not creds:
        return

    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if client.is_connected():
        logger.success("Initial connection successful")

        # Simulate disconnection
        logger.info("Simulating disconnection...")
        client.shutdown()

        # Attempt to reconnect
        logger.info("Attempting to reconnect...")
        if client.reconnect():
            logger.success("Reconnection successful!")
        else:
            logger.error("Reconnection failed")

    client.shutdown()


if __name__ == "__main__":
    # Run examples
    example_basic_connection()
    print("\n" + "="*60 + "\n")

    example_context_manager()
    print("\n" + "="*60 + "\n")

    example_reconnection()
