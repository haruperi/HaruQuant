"""Risk Limits configuration module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RiskLimits:
    """Portfolio-level hard limits and modeling parameters.

    All *_frac fields are fractions of equity (account currency).
    Example: var_cap_frac=0.10 means portfolio 1-day VaR must be <= 10% of equity.
    """

    # Hard caps (portfolio)
    var_cap_frac: float = 0.10  # hard cap for VaR (1-day)
    es_cap_frac: float = 0.15  # hard cap for Expected Shortfall (1-day)

    # Incremental caps (per new trade / adjustment)
    delta_var_cap_frac: float = 0.02  # max additional VaR allowed by one action
    delta_es_cap_frac: float = 0.03  # max additional ES allowed by one action

    # Margin safety (optional, requires MT5 margin API)
    max_margin_used_frac: float = 0.50  # e.g., don't use >50% of equity as margin

    # Correlation / stress controls
    min_pair_corr: float = 0.20  # conservative floor for off-diagonal correlations
    stressed_corr_floor: float = 0.60  # stressed floor used in STRESS regime
    use_stressed_corr: bool = True  # apply stressed floors to covariance building

    # VaR/ES settings
    confidence_level: float = 0.95
    time_horizon_days: int = 1

    # Rolling windows
    vol_lookback: int = 20
    corr_lookback: int = 60

    # Concentration controls (Risk Contribution)
    max_single_rc_frac: float = (
        0.20  # max 20% of total portfolio variance from any single symbol
    )
    rc_rebalance_tolerance: float = (
        0.05  # allowed deviation band around target RC budget in rebalancing
    )

    # Optional cluster caps (fractions of equity)
    cluster_var_caps: Optional[Dict[str, float]] = None
    cluster_es_caps: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class CorrelationPreference:
    """Soft preference to favor lower correlation additions (allocator only).

    - target_corr: prefer corr(symbol, portfolio) <= target_corr
    - penalty_strength: larger => stronger preference away from high-corr symbols
    - min_budget_frac: never reduce a symbol's base budget below this fraction
    """

    target_corr: float = 0.50
    penalty_strength: float = 2.0
    min_budget_frac: float = 0.30
