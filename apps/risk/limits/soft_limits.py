"""Soft warning rules for near-limit governance conditions."""

from __future__ import annotations

from typing import Dict, List

from .events import LimitEvent
from .models import BudgetUtilization, RiskPolicy


def evaluate_soft_limits(
    utilizations: Dict[str, BudgetUtilization],
    policy: RiskPolicy,
) -> List[LimitEvent]:
    """Return warning events for near-limit utilization."""
    warnings: List[LimitEvent] = []
    warning_frac = float(policy.warning_utilization_frac)
    if warning_frac <= 0:
        return warnings

    for key, utilization in utilizations.items():
        if utilization.utilization_frac < warning_frac or utilization.utilization_frac > 1.0:
            continue
        scope, scope_key = _parse_scope(key)
        warnings.append(
            LimitEvent(
                event_type="soft_limit",
                rule_key=f"{key}_warning",
                severity="warning",
                message=f"{key} is nearing its configured limit.",
                observed_value=utilization.observed,
                threshold_value=utilization.threshold,
                unit=utilization.unit,
                scope=scope,
                scope_key=scope_key,
                context={"utilization_frac": utilization.utilization_frac},
            )
        )
    return warnings


def _parse_scope(key: str):
    if ":" not in key:
        return "portfolio", None
    prefix, suffix = key.split(":", 1)
    if prefix.startswith("cluster_"):
        return "cluster", suffix
    return "portfolio", suffix

