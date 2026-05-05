"""Example usage of TerminalInfo with MT5/Tester backend parity."""

import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.simulation.engine import Engine

def _term_value(terminal, attr_name: str, method_name: str | None = None, default=None):
    if hasattr(terminal, attr_name):
        return getattr(terminal, attr_name)
    if method_name and hasattr(terminal, method_name):
        return getattr(terminal, method_name)()
    return default


def print_terminal_info(row):
    print("=" * 60)
    print("TerminalInfo")
    print("=" * 60)
    print(f"Build:              {_term_value(row, 'build', 'Build', 0)}")
    print(f"Connected:          {'Yes' if _term_value(row, 'connected', 'Connected', 0) else 'No'}")
    print(f"Trade Allowed:      {'Yes' if _term_value(row, 'trade_allowed', 'TradeAllowed', 0) else 'No'}")
    print(f"DLLs Allowed:       {'Yes' if _term_value(row, 'dlls_allowed', 'DLLsAllowed', 0) else 'No'}")
    print(f"Ping Last (us):     {_term_value(row, 'ping_last', 'PingLast', 0)}")
    print(f"CPU Cores:          {_term_value(row, 'cpu_cores', 'CPUCores', 0)}")
    print(f"Memory Total:       {_term_value(row, 'memory_total', 'MemoryTotal', 0)}")
    print(f"Memory Available:   {_term_value(row, 'memory_available', 'MemoryAvailable', 0)}")
    print(f"Language:           {_term_value(row, 'language', 'Language', '')}")
    print(f"Company:            {_term_value(row, 'company', 'Company', '')}")
    print(f"Name:               {_term_value(row, 'name', 'Name', '')}")
    print(f"Path:               {_term_value(row, 'path', 'Path', '')}")
    print(f"Data Path:          {_term_value(row, 'data_path', 'DataPath', '')}")
    print(f"Common Data Path:   {_term_value(row, 'commondata_path', 'CommondataPath', '')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "mt5"], default="sim")
    args = parser.parse_args()
    backend = args.backend

    engine_instance = Engine(backend=backend)
    api = engine_instance.api
    mt5_terminal = engine_instance.mt5.terminal_info()
    
    if backend == "sim":
        if hasattr(mt5_terminal, "_asdict"):
            engine_instance.state.terminal_info.update(mt5_terminal._asdict())
        elif isinstance(mt5_terminal, dict):
            engine_instance.state.terminal_info.update(mt5_terminal)
        elif mt5_terminal:
            engine_instance.state.terminal_info.update(vars(mt5_terminal))
        
        row = api.terminal_info()
        row.company = "HaruQuant Tester"
        row.name = "Tester Terminal"
        row.connected = True
        print("Using: Tester backend")
    else:
        row = api.terminal_info()
        print("Using: MT5 backend")

    print_terminal_info(row)

    engine_instance.client.shutdown()


if __name__ == "__main__":
    main()
