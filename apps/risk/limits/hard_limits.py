"""Hard governance rules for risk policy enforcement."""

from __future__ import annotations

from typing import Dict, List, Optional

from .events import LimitEvent
from .models import BudgetUtilization, RiskPolicy


def build_budget_utilizations(
    equity: float,
    current_var: float,
    new_var: float,
    delta_var: float,
    current_es: float,
    new_es: float,
    delta_es: float,
    current_margin_used: Optional[float],
    new_margin_used: Optional[float],
    max_single_rc: float,
    rc_map_new: Optional[Dict[str, float]],
    cluster_metrics: Optional[Dict[str, Dict[str, float]]],
    policy: RiskPolicy,
) -> Dict[str, BudgetUtilization]:
    """Build normalized budget utilization records for policy checks."""
    utilizations: Dict[str, BudgetUtilization] = {}
    if equity <= 0:
        return utilizations

    _add_utilization(utilizations, "portfolio_var", new_var, policy.var_cap_frac * equity, "currency")
    _add_utilization(utilizations, "portfolio_es", new_es, policy.es_cap_frac * equity, "currency")
    _add_utilization(utilizations, "delta_var", delta_var, policy.delta_var_cap_frac * equity, "currency")
    _add_utilization(utilizations, "delta_es", delta_es, policy.delta_es_cap_frac * equity, "currency")

    if current_margin_used is not None or new_margin_used is not None:
        _add_utilization(
            utilizations,
            "margin_used",
            float(new_margin_used or 0.0),
            policy.max_margin_used_frac * equity,
            "currency",
        )

    if rc_map_new:
        rc_peak = max(float(v) for v in rc_map_new.values())
        _add_utilization(
            utilizations,
            "single_rc",
            rc_peak,
            max_single_rc,
            "ratio",
        )

    if cluster_metrics:
        for cluster_key, metrics in cluster_metrics.items():
            if cluster_key in (policy.cluster_var_caps or {}):
                _add_utilization(
                    utilizations,
                    f"cluster_var:{cluster_key}",
                    float(metrics.get("var", 0.0)),
                    float(policy.cluster_var_caps[cluster_key]) * equity,
                    "currency",
                )
            if cluster_key in (policy.cluster_es_caps or {}):
                _add_utilization(
                    utilizations,
                    f"cluster_es:{cluster_key}",
                    float(metrics.get("es", 0.0)),
                    float(policy.cluster_es_caps[cluster_key]) * equity,
                    "currency",
                )
    return utilizations


def evaluate_hard_limits(
    equity: float,
    current_var: float,
    new_var: float,
    delta_var: float,
    current_es: float,
    new_es: float,
    delta_es: float,
    current_margin_used: Optional[float],
    new_margin_used: Optional[float],
    rc_map_new: Optional[Dict[str, float]],
    cluster_metrics: Optional[Dict[str, Dict[str, float]]],
    policy: RiskPolicy,
) -> List[LimitEvent]:
    """Return hard-limit breaches for a portfolio transition."""
    breaches: List[LimitEvent] = []
    if equity <= 0:
        return [
            LimitEvent(
                event_type="hard_limit",
                rule_key="invalid_equity",
                severity="breach",
                message="Account equity must be positive for governance checks.",
                observed_value=equity,
                threshold_value=0.0,
                unit="currency",
            )
        ]

    breaches.extend(
        _threshold_breach(
            "portfolio_var_cap",
            "Portfolio VaR cap exceeded.",
            new_var,
            policy.var_cap_frac * equity,
            "currency",
        )
    )
    breaches.extend(
        _threshold_breach(
            "portfolio_es_cap",
            "Portfolio ES cap exceeded.",
            new_es,
            policy.es_cap_frac * equity,
            "currency",
        )
    )
    breaches.extend(
        _threshold_breach(
            "delta_var_cap",
            "Delta VaR cap exceeded.",
            delta_var,
            policy.delta_var_cap_frac * equity,
            "currency",
        )
    )
    breaches.extend(
        _threshold_breach(
            "delta_es_cap",
            "Delta ES cap exceeded.",
            delta_es,
            policy.delta_es_cap_frac * equity,
            "currency",
        )
    )

    if current_margin_used is not None and new_margin_used is not None:
        breaches.extend(
            _threshold_breach(
                "margin_cap",
                "Margin cap exceeded.",
                new_margin_used,
                policy.max_margin_used_frac * equity,
                "currency",
            )
        )

    if rc_map_new and len(rc_map_new) > 1:
        for symbol, value in rc_map_new.items():
            if float(value) <= policy.max_single_rc_frac:
                continue
            breaches.append(
                LimitEvent(
                    event_type="hard_limit",
                    rule_key="single_rc_cap",
                    severity="breach",
                    message=f"Risk contribution cap exceeded for {symbol}.",
                    observed_value=float(value),
                    threshold_value=policy.max_single_rc_frac,
                    unit="ratio",
                    scope="symbol",
                    scope_key=symbol,
                )
            )

    for cluster_key, metrics in (cluster_metrics or {}).items():
        if cluster_key in (policy.cluster_var_caps or {}):
            threshold = float(policy.cluster_var_caps[cluster_key]) * equity
            breaches.extend(
                _threshold_breach(
                    "cluster_var_cap",
                    f"Cluster VaR cap exceeded for {cluster_key}.",
                    float(metrics.get("var", 0.0)),
                    threshold,
                    "currency",
                    scope="cluster",
                    scope_key=cluster_key,
                )
            )
        if cluster_key in (policy.cluster_es_caps or {}):
            threshold = float(policy.cluster_es_caps[cluster_key]) * equity
            breaches.extend(
                _threshold_breach(
                    "cluster_es_cap",
                    f"Cluster ES cap exceeded for {cluster_key}.",
                    float(metrics.get("es", 0.0)),
                    threshold,
                    "currency",
                    scope="cluster",
                    scope_key=cluster_key,
                )
            )

    return breaches


def _add_utilization(
    utilizations: Dict[str, BudgetUtilization],
    key: str,
    observed: float,
    threshold: float,
    unit: str,
) -> None:
    if threshold <= 0:
        return
    utilizations[key] = BudgetUtilization(
        key=key,
        observed=float(observed),
        threshold=float(threshold),
        utilization_frac=float(observed) / float(threshold),
        unit=unit,
    )


def _threshold_breach(
    rule_key: str,
    message: str,
    observed: float,
    threshold: float,
    unit: str,
    scope: str = "portfolio",
    scope_key: Optional[str] = None,
) -> List[LimitEvent]:
    if observed <= threshold:
        return []
    return [
        LimitEvent(
            event_type="hard_limit",
            rule_key=rule_key,
            severity="breach",
            message=message,
            observed_value=float(observed),
            threshold_value=float(threshold),
            unit=unit,
            scope=scope,
            scope_key=scope_key,
        )
    ]

