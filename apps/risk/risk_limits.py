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

    # ****************************************
    # HARD CAPS (fractions of equity)
    # ****************************************

    # Portfolio-level hard caps
    var_cap_frac: float = 0.10  # Portfolio VaR (1-day, 10%)
    es_cap_frac: float = 0.15  # Portfolio Expected Shortfall (1-day, 15%)

    # Incremental caps (per new trade / adjustment)
    delta_var_cap_frac: float = (
        0.02  # max additional VaR allowed per individual trade (2%)
    )
    delta_es_cap_frac: float = (
        0.03  # max additional ES allowed per individual trade (3%)
    )

    # Margin safety (optional, requires MT5 margin API)
    max_margin_used_frac: float = (
        0.50  # Max margin usage (e.g., don't use >50% of equity as margin)
    )

    # ****************************************
    # Correlation Controls
    # ****************************************

    # Correlation / stress controls
    min_pair_corr: float = 0.20  # conservative floor for off-diagonal correlations
    stressed_corr_floor: float = 0.50  # stressed floor used in STRESS regime
    use_stressed_corr: bool = True  # apply stressed floors to covariance building

    # ****************************************
    # Statistical Settings
    # ****************************************

    # VaR/ES settings
    confidence_level: float = 0.95
    time_horizon_days: int = 1

    # Rolling windows
    vol_lookback: int = 20  # Volatility lookback (24 if using H1, 5 if using D1)
    corr_lookback: int = 60  # Correlation lookback (72 if using H1, 10 if using D1)

    # Concentration controls (Risk Contribution)
    max_single_rc_frac: float = (
        0.20  # max 20% of total portfolio variance from any single symbol
    )
    rc_rebalance_tolerance: float = (
        0.05  # allowed deviation band around target RC budget in rebalancing (5%)
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
