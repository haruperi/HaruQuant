"""
Example usage of SymbolInfo with MT5/Tester backend parity.
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.trading import Engine, trade

def _sym_value(symbol, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(symbol, attr_name):
        return getattr(symbol, attr_name)
    if method_name and hasattr(symbol, method_name):
        return getattr(symbol, method_name)()
    return default


def _seed_tester_symbols(symbols: list[str]) -> list:
    out = []
    for idx, name in enumerate(symbols, start=1):
        s = trade.SymbolInfo()
        s.name = name
        s.description = f"{name} synthetic tester symbol"
        s.digits = 5 if "JPY" not in name else 3
        point = 0.00001 if "JPY" not in name else 0.001
        s.point = point
        s.spread = 15
        s.spread_float = True
        s.trade_mode = 4
        s.trade_exemode = 2
        s.trade_calc_mode = 0
        s.volume_min = 0.01
        s.volume_max = 100.0
        s.volume_step = 0.01
        s.volume_limit = 0.0
        s.trade_tick_size = point
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
        ask = bid + (15 * point)
        s.bid = bid
        s.ask = ask
        s.last = (bid + ask) / 2.0
        out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend
    symbols = ["EURUSD", "GBPUSD"]

    print("=" * 60)
    print("SymbolInfo Example (MT5/Tester Parity)")
    print("=" * 60)
    print()

    engine_instance = Engine(backend=backend)
    api = engine_instance.api

    if backend == "sim":
        symbol_rows = _seed_tester_symbols(symbols)
        engine_instance.state.trading_symbols.extend(symbol_rows)
        print("Using: Tester backend")
    else:
        symbol_rows = []
        for name in symbols:
            api.symbol_select(name, True)
            info = api.symbol_info(name)
            if info is not None:
                symbol_rows.append(info)
        print("Using: MT5 backend")

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

    all_symbols = api.symbols_get()
    print("=" * 60)

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)

    print("\nShutting down MT5 connection...")
    engine_instance.client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()
