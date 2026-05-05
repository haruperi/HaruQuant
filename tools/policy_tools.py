"""Policy tool stubs."""

from .registry import POLICY_TOOLS, make_stub_function

__all__ = list(POLICY_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
