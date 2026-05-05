"""Research tool stubs."""

from .registry import RESEARCH_TOOLS, make_stub_function

__all__ = list(RESEARCH_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
