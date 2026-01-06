"""
Example usage of TerminalInfo with MT5TerminalProvider.

This example demonstrates how to access terminal information from MT5.
Note: BacktestTerminalProvider is not yet implemented as terminal info
rarely changes during backtesting.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import TerminalInfo, MT5TerminalProvider


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


def main():
    print("=" * 60)
    print("TerminalInfo Example")
    print("=" * 60)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    print("Connecting to MT5...")
    if not client.is_connected():
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    try:
        print(f"Connected successfully!")
        print(f"Connection state: {client.connection_state.value}")
        print()

        # Create MT5TerminalProvider
        provider = MT5TerminalProvider(client)
        terminal = TerminalInfo(provider)

        # Display terminal information
        print("TERMINAL INFORMATION")
        print("-" * 60)
        print(f"Name:           {terminal.name()}")
        print(f"Company:        {terminal.company()}")
        print(f"Build:          {terminal.build()}")
        print(f"Language:       {terminal.language()}")
        print(f"Architecture:   {'64-bit' if terminal.is_x64() else '32-bit'}")
        print()

        # Display connection and permissions
        print("CONNECTION & PERMISSIONS")
        print("-" * 60)
        print(f"Connected:      {'Yes' if terminal.is_connected() else 'No'}")
        print(f"Trade Allowed:  {'Yes' if terminal.is_trade_allowed() else 'No'}")
        print(f"DLLs Allowed:   {'Yes' if terminal.is_dlls_allowed() else 'No'}")
        print(f"Email Enabled:  {'Yes' if terminal.is_email_enabled() else 'No'}")
        print(f"FTP Enabled:    {'Yes' if terminal.is_ftp_enabled() else 'No'}")
        print()

        # Display system resources
        print("SYSTEM RESOURCES")
        print("-" * 60)
        print(f"CPU Cores:      {terminal.cpu_cores()}")
        # We can use the formatted method or raw values
        print(f"Physical RAM:   {terminal.memory_physical():,} MB")
        print(f"Total Memory:   {terminal.memory_total():,} MB")
        print(f"Available:      {terminal.memory_available():,} MB")
        print(f"Used Memory:    {terminal.memory_used():,} MB")
        if terminal.memory_total() > 0:
            usage_percent = terminal.memory_used() / terminal.memory_total() * 100
            print(f"Memory Usage:   {usage_percent:.1f}%")
        print(f"Free Disk:      {terminal.disk_space():,} MB")
        print(f"OpenCL Support: Level {terminal.opencl_support()}")
        print()

        # Or use the convenience method
        print(f"Memory Summary: {terminal.format_memory_info()}")
        print()

        # Display chart and encoding settings
        print("CHART & ENCODING")
        print("-" * 60)
        print(f"Max Bars:       {terminal.max_bars():,}")
        print(f"Code Page:      {terminal.code_page()}")
        print()

        # Display paths
        print("PATHS")
        print("-" * 60)
        print(f"Installation:   {terminal.path()}")
        print(f"Data Path:      {terminal.data_path()}")
        print(f"Common Data:    {terminal.common_data_path()}")
        print(f"Data Path:      {terminal.data_path()}")
        print(f"Common Data:    {terminal.common_data_path()}")
        print()

        # Display Dictionary Info methods
        print("DICTIONARY & HELPER METHODS")
        print("-" * 60)
        print(f"System Info:    {terminal.get_system_info()}")
        print(f"Connection Info:{terminal.get_connection_info()}")
        print(f"Info Integer (Build): {terminal.info_integer('build')}")
        print(f"Info String (Name):   {terminal.info_string('name')}")
        print()

        # Display summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Terminal {terminal.name()} (Build {terminal.build()})")
        print(
            f"Running on {terminal.cpu_cores()}-core system with {terminal.memory_physical():,}MB RAM"
        )
        print(f"Status: {'Connected' if terminal.is_connected() else 'Disconnected'}")
        print(f"Trading: {'Enabled' if terminal.is_trade_allowed() else 'Disabled'}")
        print()

        print("=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Shutdown MT5 connection
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
