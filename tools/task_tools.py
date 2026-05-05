"""Task tool stubs."""

from .registry import TASK_TOOLS, make_stub_function

__all__ = list(TASK_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
