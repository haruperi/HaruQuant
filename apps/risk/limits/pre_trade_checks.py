"""Pre-trade governance evaluation helpers."""

from __future__ import annotations

from typing import Dict, List, Optional

from .circuit_breakers import evaluate_circuit_breakers
from .events import LimitEvent, PolicyDecision
from .hard_limits import build_budget_utilizations, evaluate_hard_limits
from .models import CircuitBreakerState, GovernanceState, RiskPolicy
from .soft_limits import evaluate_soft_limits


def evaluate_pre_trade(
    *,
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
    currency_exposure: Optional[Dict[str, float]],
    gross_portfolio_notional: Optional[float],
    cluster_metrics: Optional[Dict[str, Dict[str, float]]],
    policy: RiskPolicy,
    peak_equity: Optional[float] = None,
    breaker_state: Optional[CircuitBreakerState] = None,
) -> PolicyDecision:
    """Evaluate one candidate portfolio transition before execution."""
    utilizations = build_budget_utilizations(
        equity=equity,
        current_var=current_var,
        new_var=new_var,
        delta_var=delta_var,
        current_es=current_es,
        new_es=new_es,
        delta_es=delta_es,
        current_margin_used=current_margin_used,
        new_margin_used=new_margin_used,
        max_single_rc=policy.max_single_rc_frac,
        rc_map_new=rc_map_new,
        currency_exposure=currency_exposure,
        gross_portfolio_notional=gross_portfolio_notional,
        cluster_metrics=cluster_metrics,
        policy=policy,
    )
    warnings = evaluate_soft_limits(utilizations, policy)
    breaches = evaluate_hard_limits(
        equity=equity,
        current_var=current_var,
        new_var=new_var,
        delta_var=delta_var,
        current_es=current_es,
        new_es=new_es,
        delta_es=delta_es,
        current_margin_used=current_margin_used,
        new_margin_used=new_margin_used,
        rc_map_new=rc_map_new,
        currency_exposure=currency_exposure,
        gross_portfolio_notional=gross_portfolio_notional,
        cluster_metrics=cluster_metrics,
        policy=policy,
    )

    breaker_state, breaker_event = evaluate_circuit_breakers(
        policy,
        existing_state=breaker_state,
        account_equity=equity,
        peak_equity=peak_equity,
        breach_count=len(breaches),
    )
    if breaker_event is not None:
        breaches = [*breaches, breaker_event]

    decision = "REJECT" if breaches or (breaker_state and breaker_state.halt_new_risk) else "ACCEPT"
    reason = _build_reason(decision, breaches, warnings, breaker_state)
    governance_state = GovernanceState(
        status="breach" if breaches else ("warning" if warnings else "compliant"),
        decision=decision,
        reason=reason,
        warnings_count=len(warnings),
        breaches_count=len(breaches),
        utilizations=utilizations,
    )
    return PolicyDecision(
        decision=decision,
        reason=reason,
        breaches=breaches,
        warnings=warnings,
        governance_state=governance_state,
        circuit_breaker_state=breaker_state,
    )


def _build_reason(
    decision: str,
    breaches: List[LimitEvent],
    warnings: List[LimitEvent],
    breaker_state: Optional[CircuitBreakerState],
) -> str:
    if breaker_state and breaker_state.halt_new_risk and breaker_state.reason:
        return breaker_state.reason
    if breaches:
        return breaches[0].message
    if warnings:
        return warnings[0].message
    return "All risk limits satisfied."
