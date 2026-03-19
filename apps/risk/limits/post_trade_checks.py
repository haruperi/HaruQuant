"""Post-trade governance checks for existing portfolio state."""

from __future__ import annotations

from typing import Dict, Optional

from .events import PolicyDecision
from .models import CircuitBreakerState, RiskPolicy
from .pre_trade_checks import evaluate_pre_trade


def evaluate_post_trade(
    *,
    equity: float,
    portfolio_var: float,
    portfolio_es: float,
    margin_used: Optional[float],
    rc_map: Optional[Dict[str, float]],
    cluster_metrics: Optional[Dict[str, Dict[str, float]]],
    policy: RiskPolicy,
    peak_equity: Optional[float] = None,
    breaker_state: Optional[CircuitBreakerState] = None,
) -> PolicyDecision:
    """Evaluate current portfolio compliance without a new candidate trade."""
    return evaluate_pre_trade(
        equity=equity,
        current_var=portfolio_var,
        new_var=portfolio_var,
        delta_var=0.0,
        current_es=portfolio_es,
        new_es=portfolio_es,
        delta_es=0.0,
        current_margin_used=margin_used,
        new_margin_used=margin_used,
        rc_map_new=rc_map,
        cluster_metrics=cluster_metrics,
        policy=policy,
        peak_equity=peak_equity,
        breaker_state=breaker_state,
    )

