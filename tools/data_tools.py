"""Data tool stubs."""

from .registry import DATA_TOOLS, make_stub_function

__all__ = list(DATA_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
