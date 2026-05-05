"""Prop-firm compliance tool stubs."""

from .registry import PROP_FIRM_TOOLS, make_stub_function

__all__ = list(PROP_FIRM_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
