"""Canonical risk domain models.

The package exports lazily so light governance imports do not pull in
dataframe-backed market models.
"""

from __future__ import annotations

_EXPORT_MODULES = {
    "AccountSnapshot": "snapshot",
    "AccountState": "account",
    "MarketSnapshot": "snapshot",
    "MarketState": "market",
    "PortfolioSnapshot": "snapshot",
    "PortfolioState": "portfolio",
    "PositionState": "position",
    "RiskAssessmentRequest": "proposal",
    "RiskApprovalToken": "contracts",
    "RiskDecision": "decision",
    "RiskDecisionStatus": "contracts",
    "RiskGovernorDecision": "contracts",
    "RiskMemo": "contracts",
    "RiskProposal": "contracts",
    "SymbolState": "symbol",
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
