"""
Example usage of MT5 terminal_info() directly.
"""

import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.utils.logger import logger

mt5 = get_mt5_api()


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("TerminalInfo Example (Direct MT5)")
    print("=" * 70)
    print()

    creds = get_mt5_credentials()
    client = MT5Client()
    if not client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
    ):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print("Connected successfully!")
    print()

    info = mt5.terminal_info()
    if info is None:
        print("Failed to fetch terminal info.")
        client.shutdown()
        return
    data = info._asdict()

    print("TERMINAL INFORMATION")
    print("-" * 60)
    print(f"Name:           {data.get('name', '')}")
    print(f"Company:        {data.get('company', '')}")
    print(f"Build:          {data.get('build', 0)}")
    print(f"Language:       {data.get('language', '')}")
    print(f"Connected:      {'Yes' if data.get('connected', False) else 'No'}")
    print(f"Trade Allowed:  {'Yes' if data.get('trade_allowed', False) else 'No'}")
    print(f"DLLs Allowed:   {'Yes' if data.get('dlls_allowed', False) else 'No'}")
    print(f"Path:           {data.get('path', '')}")
    print(f"Data Path:      {data.get('data_path', '')}")
    print(f"Common Data:    {data.get('commondata_path', '')}")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()

