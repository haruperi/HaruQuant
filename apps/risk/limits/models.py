"""Policy and governance models for risk limit evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RiskPolicy:
    """Portfolio-level risk policy contract used by the governance layer."""

    var_cap_frac: float = 0.10
    es_cap_frac: float = 0.15
    delta_var_cap_frac: float = 0.02
    delta_es_cap_frac: float = 0.03
    max_margin_used_frac: float = 0.50

    min_pair_corr: float = 0.20
    stressed_corr_floor: float = 0.50
    use_stressed_corr: bool = True

    confidence_level: float = 0.95
    time_horizon_days: int = 1
    vol_lookback: int = 20
    corr_lookback: int = 60

    max_single_rc_frac: float = 0.20
    rc_rebalance_tolerance: float = 0.05

    cluster_var_caps: Optional[Dict[str, float]] = None
    cluster_es_caps: Optional[Dict[str, float]] = None

    warning_utilization_frac: float = 0.90
    drawdown_halt_frac: Optional[float] = None
    max_breach_count: Optional[int] = None

    def with_updates(self, **updates: Any) -> "RiskPolicy":
        """Return a new policy with only the supplied fields changed."""
        return replace(self, **updates)


RiskLimits = RiskPolicy


@dataclass(frozen=True)
class CorrelationPreference:
    """Soft preference to favor lower correlation additions (allocator only)."""

    target_corr: float = 0.50
    penalty_strength: float = 2.0
    min_budget_frac: float = 0.30


@dataclass(frozen=True)
class OverrideRecord:
    """Track a policy override applied by the governance layer."""

    field_name: str
    previous_value: Any
    new_value: Any
    reason: str
    source: str = "system"


@dataclass(frozen=True)
class CircuitBreakerState:
    """Simple governance halt state."""

    halt_new_risk: bool = False
    reason: Optional[str] = None
    breach_count: int = 0


@dataclass(frozen=True)
class BudgetUtilization:
    """Normalized utilization record for one policy budget."""

    key: str
    observed: float
    threshold: float
    utilization_frac: float
    unit: str = "ratio"


@dataclass(frozen=True)
class GovernanceState:
    """Current compliance state to attach to snapshots and decisions."""

    status: str
    decision: str
    reason: str
    warnings_count: int = 0
    breaches_count: int = 0
    utilizations: Dict[str, BudgetUtilization] = field(default_factory=dict)

