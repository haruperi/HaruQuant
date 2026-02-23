"""
Example usage of SymbolInfo with MT5/Tester backend parity.
"""

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
import haruquant.sim as csim

mt5 = get_mt5_api()


def _sym_value(symbol, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(symbol, attr_name):
        return getattr(symbol, attr_name)
    if method_name and hasattr(symbol, method_name):
        return getattr(symbol, method_name)()
    return default


def _seed_tester_symbols(simulator: "csim.TradeSimulator", symbols: list[str]) -> None:
    for idx, name in enumerate(symbols, start=1):
        s = csim.SymbolInfo()
        s.symbol_id = idx
        s.symbol = name
        s.digits = 5 if "JPY" not in name else 3
        s.point = 0.00001 if "JPY" not in name else 0.001
        s.spread = 15
        s.spread_float = True
        s.trade_mode = 4
        s.trade_exemode = 2
        s.trade_calc_mode = 0
        s.volume_min = 0.01
        s.volume_max = 100.0
        s.volume_step = 0.01
        s.volume_limit = 0.0
        s.trade_tick_size = s.point
        s.trade_tick_value = 1.0
        s.trade_tick_value_profit = 1.0
        s.trade_tick_value_loss = 1.0
        s.trade_contract_size = 100000.0
        s.margin_initial = 0.0
        s.swap_mode = 0
        s.swap_long = -2.0
        s.swap_short = 1.0
        s.swap_rollover3days = 3
        bid = 1.10000 if name == "EURUSD" else 1.27000
        ask = bid + (s.spread * s.point)
        s.bid = bid
        s.ask = ask
        simulator.set_symbol_info(s)


def main():
    backend = "tester"  # set to: "mt5" or "tester"
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
        simulator = mt5
        print("Using: MT5 backend")
    else:
        simulator = csim.TradeSimulator()
        _seed_tester_symbols(simulator, symbols)
        print("Using: Tester backend")
    print()

    for symbol_name in symbols:
        print(f"\nProcessing {symbol_name}...")
        print("=" * 60)

        selected = simulator.symbol_select(symbol_name, True)
        if not selected:
            print(f"Failed to select symbol {symbol_name}")
            continue

        symbol = simulator.symbol_info(symbol_name)
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
        print(f"Tick Size:      {_sym_value(symbol, 'trade_tick_size', 'TickSize', 0.0)}")

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
        print(f"Execution:      {_sym_value(symbol, 'trade_exemode', 'TradeExecution', 0)}")
        print(f"Calc Mode:      {_sym_value(symbol, 'trade_calc_mode', 'TradeCalcMode', 0)}")
        print(f"Stops Level:    {_sym_value(symbol, 'trade_stops_level', 'StopsLevel', 0)} points")
        print(f"Freeze Level:   {_sym_value(symbol, 'trade_freeze_level', 'FreezeLevel', 0)} points")

        print("\nLOT PARAMETERS")
        print("-" * 60)
        print(f"Contract Size:  {float(_sym_value(symbol, 'trade_contract_size', 'ContractSize', 0.0)):.2f}")
        print(f"Min Lot:        {float(_sym_value(symbol, 'volume_min', 'LotsMin', 0.0)):.2f}")
        print(f"Max Lot:        {float(_sym_value(symbol, 'volume_max', 'LotsMax', 0.0)):.2f}")
        print(f"Lot Step:       {float(_sym_value(symbol, 'volume_step', 'LotsStep', 0.0)):.2f}")

        print("\nSWAP INFORMATION")
        print("-" * 60)
        print(f"Swap Mode:      {_sym_value(symbol, 'swap_mode', 'SwapMode', 0)}")
        print(f"Swap Long:      {float(_sym_value(symbol, 'swap_long', 'SwapLong', 0.0)):.2f}")
        print(f"Swap Short:     {float(_sym_value(symbol, 'swap_short', 'SwapShort', 0.0)):.2f}")

    all_symbols = simulator.symbols_get() or []
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
