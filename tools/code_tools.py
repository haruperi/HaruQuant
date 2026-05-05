"""Strategy code tool stubs."""

from .registry import CODE_TOOLS, make_stub_function

__all__ = list(CODE_TOOLS)
globals().update({name: make_stub_function(name) for name in __all__})
