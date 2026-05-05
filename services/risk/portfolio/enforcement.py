"""Advisory-only enforcement for portfolio proposals."""

from __future__ import annotations

from .proposals import AdvisoryPortfolioProposal

from services.utils.logger import logger

def enforce_portfolio_advisory_only(
    proposal: AdvisoryPortfolioProposal,
    *,
    requested_live_execution: bool,
) -> AdvisoryPortfolioProposal:
    """Fail closed if a portfolio proposal is used as a live execution action."""

    if requested_live_execution:
        raise ValueError("portfolio actions are advisory-only and cannot execute live")
    return proposal


__all__ = [
    "enforce_portfolio_advisory_only",
]
