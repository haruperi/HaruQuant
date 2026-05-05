"""Optimization method entry points."""

from __future__ import annotations

_EXPORT_MODULES = {
    "bayesian_optimization": "bayesian",
    "genetic_algorithm": "genetic",
    "grid_search": "grid_search",
    "random_search": "random_search",
    "walk_forward_optimization": "services.optimization.walk_forward",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(module_name if module_name.startswith("services.") else f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
