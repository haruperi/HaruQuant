"""Live execution tool stubs."""

from .registry import LIVE_EXECUTION_TOOLS, make_stub_function

__all__ = list(LIVE_EXECUTION_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
