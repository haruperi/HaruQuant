"""
Example usage of SymbolInfo with MT5/Tester backend parity.
"""

import os
import sys
import argparse

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


def _sym_value(symbol, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(symbol, attr_name):
        return getattr(symbol, attr_name)
    if method_name and hasattr(symbol, method_name):
        return getattr(symbol, method_name)()
    return default


def _safe_long(value: int | float | None) -> int:
    if value is None:
        return 0
    v = int(value)
    lo = -(2**31)
    hi = (2**31) - 1
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _seed_tester_symbols(symbols: list[str]) -> list[core.SymbolInfo]:
    out: list[core.SymbolInfo] = []
    for idx, name in enumerate(symbols, start=1):
        s = core.SymbolInfo()
        s.SetName(name)
        s.SetDescription(f"{name} synthetic tester symbol")
        s.SetDigits(5 if "JPY" not in name else 3)
        point = 0.00001 if "JPY" not in name else 0.001
        s.SetPoint(point)
        s.SetSpread(15)
        s.SetSpreadFloat(True)
        s.SetTradeMode(4)
        s.SetTradeExemode(2)
        s.SetTradeCalcMode(0)
        s.SetVolumeMin(0.01)
        s.SetVolumeMax(100.0)
        s.SetVolumeStep(0.01)
        s.SetVolumeLimit(0.0)
        s.SetTradeTickSize(point)
        s.SetTradeTickValue(1.0)
        s.SetTradeTickValueProfit(1.0)
        s.SetTradeTickValueLoss(1.0)
        s.SetTradeContractSize(100000.0)
        s.SetMarginInitial(0.0)
        s.SetSwapMode(0)
        s.SetSwapLong(-2.0)
        s.SetSwapShort(1.0)
        s.SetSwapRollover3days(3)
        bid = 1.10000 if name == "EURUSD" else 1.27000
        ask = bid + (15 * point)
        s.SetBid(bid)
        s.SetAsk(ask)
        s.SetLast((bid + ask) / 2.0)
        out.append(s)
    return out


def _mt5_symbols_to_core(symbols: list[str]) -> list[core.SymbolInfo]:
    out: list[core.SymbolInfo] = []
    for name in symbols:
        mt5.symbol_select(name, True)
        info = mt5.symbol_info(name)
        if info is None:
            continue
        s = core.SymbolInfo()
        s.SetName(str(getattr(info, "name", name)))
        s.SetDescription(str(getattr(info, "description", "")))
        s.SetPath(str(getattr(info, "path", "")))
        s.SetDigits(_safe_long(getattr(info, "digits", 0)))
        s.SetPoint(float(getattr(info, "point", 0.0)))
        s.SetSpread(_safe_long(getattr(info, "spread", 0)))
        s.SetSpreadFloat(bool(getattr(info, "spread_float", False)))
        s.SetTradeMode(_safe_long(getattr(info, "trade_mode", 0)))
        s.SetTradeExemode(_safe_long(getattr(info, "trade_exemode", 0)))
        s.SetTradeCalcMode(_safe_long(getattr(info, "trade_calc_mode", 0)))
        s.SetTradeStopsLevel(_safe_long(getattr(info, "trade_stops_level", 0)))
        s.SetTradeFreezeLevel(_safe_long(getattr(info, "trade_freeze_level", 0)))
        s.SetVolumeMin(float(getattr(info, "volume_min", 0.0)))
        s.SetVolumeMax(float(getattr(info, "volume_max", 0.0)))
        s.SetVolumeStep(float(getattr(info, "volume_step", 0.0)))
        s.SetVolumeLimit(float(getattr(info, "volume_limit", 0.0)))
        s.SetTradeTickSize(float(getattr(info, "trade_tick_size", 0.0)))
        s.SetTradeTickValue(float(getattr(info, "trade_tick_value", 0.0)))
        s.SetTradeTickValueProfit(float(getattr(info, "trade_tick_value_profit", 0.0)))
        s.SetTradeTickValueLoss(float(getattr(info, "trade_tick_value_loss", 0.0)))
        s.SetTradeContractSize(float(getattr(info, "trade_contract_size", 0.0)))
        s.SetMarginInitial(float(getattr(info, "margin_initial", 0.0)))
        s.SetMarginMaintenance(float(getattr(info, "margin_maintenance", 0.0)))
        s.SetSwapMode(_safe_long(getattr(info, "swap_mode", 0)))
        s.SetSwapLong(float(getattr(info, "swap_long", 0.0)))
        s.SetSwapShort(float(getattr(info, "swap_short", 0.0)))
        s.SetSwapRollover3days(_safe_long(getattr(info, "swap_rollover3days", 0)))
        s.SetCurrencyBase(str(getattr(info, "currency_base", "")))
        s.SetCurrencyProfit(str(getattr(info, "currency_profit", "")))
        s.SetCurrencyMargin(str(getattr(info, "currency_margin", "")))
        s.SetBid(float(getattr(info, "bid", 0.0)))
        s.SetAsk(float(getattr(info, "ask", 0.0)))
        s.SetLast(float(getattr(info, "last", 0.0)))
        s.SetTime(_safe_long(getattr(info, "time", 0)))
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["tester", "mt5"], default="tester")
    args = parser.parse_args()
    backend = args.backend
    symbols = ["EURUSD", "GBPUSD"]

    print("=" * 60)
    print("SymbolInfo Example (MT5/Tester Parity)")
    print("=" * 60)
    print()

    client = None
    if backend == "mt5":
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5.")
            return
        symbol_rows = _mt5_symbols_to_core(symbols)
        print("Using: MT5 backend")
    else:
        client = MT5Utils.get_connected_client()
        if client is None:
            print("Failed to connect to MT5 (required for base account in tester mode).")
            return
        mt5_account = client.account_info()
        account = core.AccountInfo(mt5_account)
        _backtest_simulator = core.BacktestSimulator(account)
        symbol_rows = _seed_tester_symbols(symbols)
        print("Using: Tester backend")
    print()

    for symbol_name in symbols:
        print(f"\nProcessing {symbol_name}...")
        print("=" * 60)
        symbol = next((s for s in symbol_rows if _sym_value(s, "name", "Name", "") == symbol_name), None)
        if symbol is None:
            print(f"Failed to get symbol {symbol_name}")
            continue

        digits = int(_sym_value(symbol, "digits", "Digits", 5) or 5)

        print("\nBASIC INFORMATION")
        print("-" * 60)
        print(f"Symbol:         {_sym_value(symbol, 'name', 'Name', symbol_name)}")
        print(f"Description:    {_sym_value(symbol, 'description', 'Description', '')}")
        print(f"Path:           {_sym_value(symbol, 'path', 'Path', '')}")
        print(f"Digits:         {digits}")
        print(f"Point:          {_sym_value(symbol, 'point', 'Point', 0.0)}")
        print(f"Tick Size:      {_sym_value(symbol, 'trade_tick_size', 'TradeTickSize', 0.0)}")

        print("\nCURRENT PRICES")
        print("-" * 60)
        bid = float(_sym_value(symbol, "bid", "Bid", 0.0) or 0.0)
        ask = float(_sym_value(symbol, "ask", "Ask", 0.0) or 0.0)
        last = float(_sym_value(symbol, "last", "Last", 0.0) or 0.0)
        spread = _sym_value(symbol, "spread", "Spread", 0)
        spread_float = _sym_value(symbol, "spread_float", "SpreadFloat", False)
        print(f"Bid:            {bid:.{digits}f}")
        print(f"Ask:            {ask:.{digits}f}")
        print(f"Last:           {last:.{digits}f}")
        print(f"Spread:         {spread} points")
        print(f"Spread Float:   {'Yes' if spread_float else 'No'}")

        print("\nTRADING INFORMATION")
        print("-" * 60)
        print(f"Trade Mode:     {_sym_value(symbol, 'trade_mode', 'TradeMode', 0)}")
        print(f"Execution:      {_sym_value(symbol, 'trade_exemode', 'TradeExemode', 0)}")
        print(f"Calc Mode:      {_sym_value(symbol, 'trade_calc_mode', 'TradeCalcMode', 0)}")
        print(f"Stops Level:    {_sym_value(symbol, 'trade_stops_level', 'TradeStopsLevel', 0)} points")
        print(f"Freeze Level:   {_sym_value(symbol, 'trade_freeze_level', 'TradeFreezeLevel', 0)} points")

        print("\nLOT PARAMETERS")
        print("-" * 60)
        print(f"Contract Size:  {float(_sym_value(symbol, 'trade_contract_size', 'TradeContractSize', 0.0)):.2f}")
        print(f"Min Lot:        {float(_sym_value(symbol, 'volume_min', 'VolumeMin', 0.0)):.2f}")
        print(f"Max Lot:        {float(_sym_value(symbol, 'volume_max', 'VolumeMax', 0.0)):.2f}")
        print(f"Lot Step:       {float(_sym_value(symbol, 'volume_step', 'VolumeStep', 0.0)):.2f}")

        print("\nSWAP INFORMATION")
        print("-" * 60)
        print(f"Swap Mode:      {_sym_value(symbol, 'swap_mode', 'SwapMode', 0)}")
        print(f"Swap Long:      {float(_sym_value(symbol, 'swap_long', 'SwapLong', 0.0)):.2f}")
        print(f"Swap Short:     {float(_sym_value(symbol, 'swap_short', 'SwapShort', 0.0)):.2f}")

    all_symbols = symbol_rows
    print("\n" + "=" * 60)
    print(f"symbols_get() count: {len(all_symbols)}")
    print("=" * 60)

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)

    if client is not None:
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
