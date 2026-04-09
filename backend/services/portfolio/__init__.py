"""Portfolio analytics services."""

from .contributions import MarginalRiskContribution, calculate_marginal_risk_contribution
from .enforcement import enforce_portfolio_advisory_only
from .impacts import (
    ProjectedVarEsImpact,
    calculate_projected_margin_impact,
    calculate_projected_var_es_impact,
)
from .proposals import (
    AdvisoryPortfolioProposal,
    generate_derisk_proposal,
    generate_hedge_proposal,
    generate_rebalance_proposal,
    generate_resize_proposal,
)
from .snapshots import PortfolioSnapshotAssemblyInput, assemble_portfolio_snapshot

__all__ = [
    "AdvisoryPortfolioProposal",
    "MarginalRiskContribution",
    "PortfolioSnapshotAssemblyInput",
    "ProjectedVarEsImpact",
    "calculate_projected_margin_impact",
    "calculate_marginal_risk_contribution",
    "calculate_projected_var_es_impact",
    "enforce_portfolio_advisory_only",
    "generate_derisk_proposal",
    "generate_hedge_proposal",
    "generate_rebalance_proposal",
    "generate_resize_proposal",
    "assemble_portfolio_snapshot",
]
