"""Simulation and backtest tool stubs."""

from .registry import SIMULATION_TOOLS, make_stub_function

__all__ = list(SIMULATION_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
