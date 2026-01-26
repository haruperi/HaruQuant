"""
CTerminalInfo usage example (MT5 Standard Library).

This example demonstrates:
- Connecting to MT5 using stored credentials
- Accessing terminal properties
"""

import os
import sys

import MetaTrader5 as mt5

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.ctrade import CTerminalInfo
from apps.logger import logger
from apps.sqlite.users import UserManager


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main() -> None:
    logger.info("=== CTerminalInfo Example ===")

    creds = get_mt5_credentials()

    if not mt5.initialize(
        path=creds["path"],
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
    ):
        error = mt5.last_error()
        logger.error(f"MT5 initialize failed: {error}")
        return

    try:
        terminal = CTerminalInfo()

        logger.info(f"Name: {terminal.Name()}")
        logger.info(f"Company: {terminal.Company()}")
        logger.info(f"Build: {terminal.Build()}")
        logger.info(f"Language: {terminal.Language()}")
        logger.info(f"Connected: {terminal.IsConnected()}")
        logger.info(f"Trade Allowed: {terminal.IsTradeAllowed()}")
        logger.info(f"DLLs Allowed: {terminal.IsDLLsAllowed()}")
        logger.info(f"Email Enabled: {terminal.IsEmailEnabled()}")
        logger.info(f"FTP Enabled: {terminal.IsFtpEnabled()}")
        logger.info(f"CPU Cores: {terminal.CPUCores()}")
        logger.info(f"Memory Total: {terminal.MemoryTotal()} MB")
        logger.info(f"Memory Available: {terminal.MemoryAvailable()} MB")
        logger.info(f"Disk Space: {terminal.DiskSpace()} MB")
        logger.info(f"Path: {terminal.Path()}")
        logger.info(f"Data Path: {terminal.DataPath()}")
        logger.info(f"Common Data Path: {terminal.CommonDataPath()}")

    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete")


if __name__ == "__main__":
    main()
