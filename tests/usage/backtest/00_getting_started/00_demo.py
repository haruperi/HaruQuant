"""
Basic Demonstration of using the C++ backtest engine

Usage:
    python tests/usage/backtest/00_getting_started/00_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BRIDGE_BUILD_DIR = PROJECT_ROOT / "build" / "bridge" / "Release"

# Prefer the local dev build of the C++ extension.
if str(BRIDGE_BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_BUILD_DIR))

# Ensure dependent DLLs (fmt/spdlog) are discoverable on Windows.
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(BRIDGE_BUILD_DIR))


def main() -> None:
    import hqt_engine.sim as sim

    account = sim.AccountInfo(10_000.0, "USD", 100)
    account.login = 12345678
    account.name = "Simulated Trader"
    account.server = "Sim-Server"
    account.company = "Simulated Company"

    simulator = sim.TradeSimulator(account)
    snapshot = simulator.account_info()

    print("TradeSimulator initialized")
    print(
        f"balance={snapshot.balance:.2f} "
        f"leverage={snapshot.leverage} "
        f"currency={snapshot.currency}"
    )


if __name__ == "__main__":
    main()
