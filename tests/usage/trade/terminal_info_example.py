"""
Example usage of TerminalInfo with different providers.
"""

import sys
import os

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trade import TerminalInfo
from apps.trade.simulator_data import SimulatorClient, TerminalInfoSimulator


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
    print("=" * 70)
    print("TerminalInfo Example")
    print("=" * 70)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not connected:
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print(f"Connected successfully!")
    print()

    # ============================================================
    # CHOOSE YOUR OPTION
    # ============================================================

    # Option 1: Live Trading with MT5 (Default)
    # terminal = TerminalInfo()
    # print("Using: MT5 Live Connection")

    # Option 2: Simulator (Uncomment to use)
    sim_terminal = TerminalInfoSimulator(
        name="HaruQuant Simulator", company="HaruCorp", build=1234, connected=True
    )
    simulator = SimulatorClient(terminal_data=sim_terminal)
    terminal = TerminalInfo(api=simulator)
    print("Using: Simulator (Simulated Terminal)")

    print()

    # Display terminal information
    print("TERMINAL INFORMATION")
    print("-" * 60)
    print(f"Name:           {terminal.Name()}")
    print(f"Company:        {terminal.Company()}")
    print(f"Build:          {terminal.Build()}")
    print(f"Language:       {terminal.Language()}")
    print(f"Architecture:   {'64-bit' if terminal.IsX64() else '32-bit'}")
    print()

    # Display connection and permissions
    print("CONNECTION & PERMISSIONS")
    print("-" * 60)
    print(f"Connected:      {'Yes' if terminal.IsConnected() else 'No'}")
    print(f"Trade Allowed:  {'Yes' if terminal.IsTradeAllowed() else 'No'}")
    print(f"DLLs Allowed:   {'Yes' if terminal.IsDLLsAllowed() else 'No'}")
    print(f"Email Enabled:  {'Yes' if terminal.IsEmailEnabled() else 'No'}")
    print(f"FTP Enabled:    {'Yes' if terminal.IsFtpEnabled() else 'No'}")
    print()

    # Display system resources
    print("SYSTEM RESOURCES")
    print("-" * 60)
    print(f"CPU Cores:      {terminal.CPUCores()}")
    print(f"Physical RAM:   {terminal.MemoryPhysical():,} MB")
    print(f"Total Memory:   {terminal.MemoryTotal():,} MB")
    print(f"Available:      {terminal.MemoryAvailable():,} MB")
    print(f"Used Memory:    {terminal.MemoryUsed():,} MB")
    
    if terminal.MemoryTotal() > 0:
        usage_percent = terminal.MemoryUsed() / terminal.MemoryTotal() * 100
        print(f"Memory Usage:   {usage_percent:.1f}%")
        
    print(f"Free Disk:      {terminal.DiskSpace():,} MB")
    print(f"OpenCL Support: Level {terminal.OpenCLSupport()}")
    print()

    # Display chart and encoding settings
    print("CHART & ENCODING")
    print("-" * 60)
    print(f"Max Bars:       {terminal.MaxBars():,}")
    print(f"Code Page:      {terminal.CodePage()}")
    print()

    # Display paths
    print("PATHS")
    print("-" * 60)
    print(f"Installation:   {terminal.Path()}")
    print(f"Data Path:      {terminal.DataPath()}")
    print(f"Common Data:    {terminal.CommonDataPath()}")
    print()

    # Display Dictionary Info methods
    print("DICTIONARY & HELPER METHODS")
    print("-" * 60)
    print(f"System Info:    {terminal.GetSystemInfo()}")
    print(f"Connection Info:{terminal.GetConnectionInfo()}")
    print(f"Info Integer (Build): {terminal.InfoInteger('build')}")
    print(f"Info String (Name):   {terminal.InfoString('name')}")
    print()

    # Display summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Terminal {terminal.Name()} (Build {terminal.Build()})")
    print(f"Status: {'Connected' if terminal.IsConnected() else 'Disconnected'}")
    print(f"Trading: {'Enabled' if terminal.IsTradeAllowed() else 'Disabled'}")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
