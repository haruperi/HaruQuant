"""Trade proposal domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import RiskProposal


@dataclass(frozen=True)
class RiskAssessmentRequest:
    """Public request envelope for pre-trade risk assessment."""

    proposal: dict[str, Any] | RiskProposal
    portfolio_snapshot: dict[str, Any] = field(default_factory=dict)
    market_snapshot: dict[str, Any] = field(default_factory=dict)


__all__ = ["RiskAssessmentRequest", "RiskProposal"]
