"""Risk recommendation and optimization helpers."""

from __future__ import annotations

_EXPORT_MODULES = {
    "AllocationPlanner": "allocation_planner",
    "AllocationOptimizer": "allocation_optimizer",
    "CapitalEfficiencyRanker": "capital_efficiency",
    "HedgeOptimizer": "hedge_optimizer",
    "MarginalRiskEvaluator": "marginal_risk",
    "RecommendationAction": "models",
    "RecommendationBatch": "models",
    "RecommendationResult": "models",
    "RecommendationScore": "models",
    "RebalanceSuggestionEngine": "rebalance_suggestions",
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
