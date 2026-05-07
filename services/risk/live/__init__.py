"""Live risk controls layered on top of canonical risk services."""

from __future__ import annotations

_EXPORT_MODULES = {
    "broker_risk_state": "broker_risk",
    "PortfolioManager": "portfolio_manager",
    "RiskIntegratedEngine": "engine",
    "SafetyChecker": "safety_checks",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
