"""Portfolio analytics services."""

from __future__ import annotations

_EXPORT_MODULES = {
    "AdvisoryPortfolioProposal": "proposals",
    "MarginalRiskContribution": "contributions",
    "PortfolioSnapshotAssemblyInput": "snapshots",
    "PortfolioStateBuilder": "state_builder",
    "PortfolioStateEngine": "state_builder",
    "ProjectedVarEsImpact": "impacts",
    "RiskSnapshotBuilder": "snapshot_builder",
    "RiskSnapshotEngine": "snapshot_builder",
    "assemble_portfolio_snapshot": "snapshots",
    "calculate_marginal_risk_contribution": "contributions",
    "calculate_projected_margin_impact": "impacts",
    "calculate_projected_var_es_impact": "impacts",
    "enforce_portfolio_advisory_only": "enforcement",
    "generate_derisk_proposal": "proposals",
    "generate_hedge_proposal": "proposals",
    "generate_rebalance_proposal": "proposals",
    "generate_resize_proposal": "proposals",
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
