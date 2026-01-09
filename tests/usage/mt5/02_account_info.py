"""
MT5 Client - Account Information Example

This example demonstrates:
- Retrieving account information
- Retrieving terminal information
- Accessing cached data
"""

import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger





def example_account_information():
    """Example: Retrieve and display account information."""
    logger.info("=== Account Information Example ===")

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

        # Get account information
        account_info = client.get_account_info()
        if account_info:
            logger.info("Account Information:")
            logger.info(f"  Login: {account_info.get('login', 'N/A')}")
            logger.info(f"  Server: {account_info.get('server', 'N/A')}")
            logger.info(f"  Balance: {account_info.get('balance', 'N/A')}")
            logger.info(f"  Equity: {account_info.get('equity', 'N/A')}")
            logger.info(f"  Margin: {account_info.get('margin', 'N/A')}")
            logger.info(f"  Free Margin: {account_info.get('margin_free', 'N/A')}")
            logger.info(f"  Margin Level: {account_info.get('margin_level', 'N/A')}%")
            logger.info(f"  Profit: {account_info.get('profit', 'N/A')}")
            logger.info(f"  Currency: {account_info.get('currency', 'N/A')}")
            logger.info(f"  Leverage: 1:{account_info.get('leverage', 'N/A')}")
            logger.info(f"  Trade Mode: {account_info.get('trade_mode', 'N/A')}")

            # Access cached data
            logger.info("\nAccessing cached account info:")
            logger.info(f"  Cached Balance: {client.account_info.get('balance', 'N/A')}")


def example_terminal_information():
    """Example: Retrieve and display terminal information."""
    logger.info("=== Terminal Information Example ===")

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

        # Get terminal information
        terminal_info = client.get_terminal_info()
        if terminal_info:
            logger.info("Terminal Information:")
            logger.info(f"  Company: {terminal_info.get('company', 'N/A')}")
            logger.info(f"  Name: {terminal_info.get('name', 'N/A')}")
            logger.info(f"  Build: {terminal_info.get('build', 'N/A')}")
            logger.info(f"  Path: {terminal_info.get('path', 'N/A')}")
            logger.info(f"  Data Path: {terminal_info.get('data_path', 'N/A')}")
            logger.info(f"  Connected: {terminal_info.get('connected', 'N/A')}")
            logger.info(f"  Trade Allowed: {terminal_info.get('trade_allowed', 'N/A')}")
            logger.info(f"  DLLs Allowed: {terminal_info.get('dlls_allowed', 'N/A')}")
            logger.info(f"  Email Enabled: {terminal_info.get('email_enabled', 'N/A')}")
            logger.info(f"  FTP Enabled: {terminal_info.get('ftp_enabled', 'N/A')}")
            logger.info(f"  Notifications Enabled: {terminal_info.get('notifications_enabled', 'N/A')}")

            # Access cached data
            logger.info("\nAccessing cached terminal info:")
            logger.info(f"  Cached Build: {client.terminal_info.get('build', 'N/A')}")


def example_connection_statistics():
    """Example: Display connection statistics."""
    logger.info("=== Connection Statistics Example ===")

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

    if client.is_connected():
        logger.info("Connection Statistics:")
        logger.info(f"  Connection Attempts: {client._connection_attempts}")
        logger.info(f"  Successful Connections: {client._successful_connections}")
        logger.info(f"  Failed Connections: {client._failed_connections}")
        logger.info(f"  Last Connection Time: {client._last_connection_time}")
        logger.info(f"  Current State: {client.connection_state}")

        # Test reconnection statistics
        client.shutdown()
        client.reconnect()

        logger.info("\nAfter reconnection:")
        logger.info(f"  Connection Attempts: {client._connection_attempts}")
        logger.info(f"  Successful Connections: {client._successful_connections}")
        logger.info(f"  Failed Connections: {client._failed_connections}")

    client.shutdown()


if __name__ == "__main__":
    # Run examples
    example_account_information()
    print("\n" + "="*60 + "\n")

    example_terminal_information()
    print("\n" + "="*60 + "\n")

    example_connection_statistics()
