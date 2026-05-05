"""Broker bridge tool stubs."""

from .registry import BROKER_TOOLS, make_stub_function

__all__ = list(BROKER_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
