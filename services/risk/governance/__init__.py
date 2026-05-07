"""Risk governance, approvals, audit, and fail-closed controls."""

from __future__ import annotations

_EXPORT_MODULES = {
    "DEFAULT_RISK_THRESHOLDS": "governor",
    "GovernanceEngine": "governance_engine",
    "GovernanceReport": "governance_engine",
    "RiskGovernor": "governor",
    "RiskGovernorDecision": "governor",
    "create_approval_token": "approval_tokens",
    "validate_approval_token": "approval_tokens",
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
