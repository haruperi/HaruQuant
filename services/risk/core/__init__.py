"""Core risk orchestration helpers."""

from __future__ import annotations

_EXPORT_MODULES = {
    "GovernanceEngine": "governance_engine",
    "GovernanceReport": "governance_engine",
    "PortfolioRiskEngine": "portfolio_risk_engine",
    "PortfolioStateEngine": "portfolio_state_engine",
    "RecommendationEngine": "recommendation_engine",
    "RiskScorecardEngine": "risk_scorecard_engine",
    "RiskSnapshotEngine": "risk_snapshot_engine",
    "TimelinePoint": "timeline_reconstructor",
    "TimelineReconstructor": "timeline_reconstructor",
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
