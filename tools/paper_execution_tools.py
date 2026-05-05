"""Paper execution tool stubs."""

from .registry import PAPER_EXECUTION_TOOLS, make_stub_function

__all__ = list(PAPER_EXECUTION_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
