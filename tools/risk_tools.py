"""Risk tool stubs."""

from .registry import RISK_TOOLS, make_stub_function

__all__ = list(RISK_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
