"""Memory and evidence tool stubs."""

from .registry import MEMORY_TOOLS, make_stub_function

__all__ = list(MEMORY_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
