"""Reporting tool stubs."""

from .registry import REPORTING_TOOLS, make_stub_function

__all__ = list(REPORTING_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
