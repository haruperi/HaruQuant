"""Example usage of TerminalInfo with MT5/Tester backend parity."""

import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

from apps.mt5 import MT5Utils, get_mt5_api
import haruquant.core as core

mt5 = get_mt5_api()


def _safe_long(value) -> int:
    if value is None:
        return 0
    try:
        v = int(value)
    except Exception:
        return 0
    lo = -(2**31)
    hi = (2**31) - 1
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _mt5_terminal_to_core(mt5_terminal) -> core.TerminalInfo:
    row = core.TerminalInfo()
    if mt5_terminal is None:
        return row

    row.SetBuild(_safe_long(getattr(mt5_terminal, "build", 0)))
    row.SetCommunityAccount(_safe_long(getattr(mt5_terminal, "community_account", 0)))
    row.SetCommunityConnection(_safe_long(getattr(mt5_terminal, "community_connection", 0)))
    row.SetConnected(_safe_long(getattr(mt5_terminal, "connected", 0)))
    row.SetDLLsAllowed(_safe_long(getattr(mt5_terminal, "dlls_allowed", 0)))
    row.SetTradeAllowed(_safe_long(getattr(mt5_terminal, "trade_allowed", 0)))
    row.SetEmailEnabled(_safe_long(getattr(mt5_terminal, "email_enabled", 0)))
    row.SetFtpEnabled(_safe_long(getattr(mt5_terminal, "ftp_enabled", 0)))
    row.SetNotificationsEnabled(_safe_long(getattr(mt5_terminal, "notifications_enabled", 0)))
    row.SetMaxBars(_safe_long(getattr(mt5_terminal, "maxbars", 0)))
    row.SetMQID(_safe_long(getattr(mt5_terminal, "mqid", 0)))
    row.SetCodePage(_safe_long(getattr(mt5_terminal, "codepage", 0)))
    row.SetCPUCores(_safe_long(getattr(mt5_terminal, "cpu_cores", 0)))
    row.SetDiskSpace(_safe_long(getattr(mt5_terminal, "disk_space", 0)))
    row.SetMemoryPhysical(_safe_long(getattr(mt5_terminal, "memory_physical", 0)))
    row.SetMemoryTotal(_safe_long(getattr(mt5_terminal, "memory_total", 0)))
    row.SetMemoryAvailable(_safe_long(getattr(mt5_terminal, "memory_available", 0)))
    row.SetMemoryUsed(_safe_long(getattr(mt5_terminal, "memory_used", 0)))
    row.SetX64(_safe_long(getattr(mt5_terminal, "x64", 0)))
    row.SetOpenCLSupport(_safe_long(getattr(mt5_terminal, "opencl_support", 0)))
    row.SetPingLast(_safe_long(getattr(mt5_terminal, "ping_last", 0)))

    row.SetLanguage(str(getattr(mt5_terminal, "language", "")))
    row.SetCompany(str(getattr(mt5_terminal, "company", "")))
    row.SetName(str(getattr(mt5_terminal, "name", "")))
    row.SetPath(str(getattr(mt5_terminal, "path", "")))
    row.SetDataPath(str(getattr(mt5_terminal, "data_path", "")))
    row.SetCommondataPath(str(getattr(mt5_terminal, "commondata_path", "")))
    return row


def print_terminal_info(row: core.TerminalInfo):
    print("=" * 60)
    print("TerminalInfo")
    print("=" * 60)
    print(f"Build:              {row.Build()}")
    print(f"Connected:          {row.Connected()}")
    print(f"Trade Allowed:      {row.TradeAllowed()}")
    print(f"DLLs Allowed:       {row.DLLsAllowed()}")
    print(f"Ping Last (us):     {row.PingLast()}")
    print(f"CPU Cores:          {row.CPUCores()}")
    print(f"Memory Total:       {row.MemoryTotal()}")
    print(f"Memory Available:   {row.MemoryAvailable()}")
    print(f"Language:           {row.Language()}")
    print(f"Company:            {row.Company()}")
    print(f"Name:               {row.Name()}")
    print(f"Path:               {row.Path()}")
    print(f"Data Path:          {row.DataPath()}")
    print(f"Common Data Path:   {row.CommondataPath()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["tester", "mt5"], default="tester")
    args = parser.parse_args()
    backend = args.backend

    client = MT5Utils.get_connected_client()
    if client is None:
        print("Failed to connect to MT5.")
        return

    mt5_account = client.account_info()
    mt5_terminal = mt5.terminal_info()

    if backend == "tester":
        account = core.AccountInfo(mt5_account)
        _simulator = core.BacktestSimulator(account)
        row = _mt5_terminal_to_core(mt5_terminal)
        row.SetCompany("HaruQuant Tester")
        row.SetName("Tester Terminal")
        row.SetConnected(1)
        print("Using: Tester backend")
    else:
        row = _mt5_terminal_to_core(mt5_terminal)
        print("Using: MT5 backend")

    print_terminal_info(row)

    client.shutdown()


if __name__ == "__main__":
    main()
