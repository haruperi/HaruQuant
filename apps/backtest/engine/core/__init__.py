"""
Core Simulation Engine.

High-performance backtesting core using NumPy and optional Numba JIT compilation.
Provides 50-100x speedup over pure Python event-driven simulation.

Modules:
    - types: NumPy-friendly data structures
    - simulator: JIT-compiled simulation loop
    - signals: Signal preparation utilities
"""

from .signals import (
    extract_ohlc_arrays,
    prepare_signals_from_dataframe,
    prepare_signals_from_list,
    prepare_simulation_inputs,
)
from .simulator import is_numba_available, run_simulation, run_simulation_python
from .types import SimulationConfig, SimulationResult, TradeResult

__all__ = [
    # Types
    "SimulationConfig",
    "TradeResult",
    "SimulationResult",
    # Simulator
    "run_simulation",
    "run_simulation_python",
    "is_numba_available",
    # Signals
    "prepare_signals_from_dataframe",
    "prepare_signals_from_list",
    "extract_ohlc_arrays",
    "prepare_simulation_inputs",
]
