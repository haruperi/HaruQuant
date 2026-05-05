"""Analytics tool stubs."""

from .registry import ANALYTICS_TOOLS, make_stub_function

__all__ = list(ANALYTICS_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
