"""Audit tool stubs."""

from .registry import AUDIT_TOOLS, make_stub_function

__all__ = list(AUDIT_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
