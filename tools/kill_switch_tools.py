"""Kill-switch tool stubs."""

from .registry import KILL_SWITCH_TOOLS, make_stub_function

__all__ = list(KILL_SWITCH_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
