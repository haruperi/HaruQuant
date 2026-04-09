"""Risk decision outcome composition for deterministic safety checks."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.risk_assessment_decision.model import LimitConstraint

from .restrictions import RestrictionEvaluation


@dataclass(frozen=True)
class ComposedRiskDecision:
    """Minimal risk decision outcome before envelope/provenance packing."""

    decision: str
    reasons: tuple[str, ...]
    limit_constraints: tuple[LimitConstraint, ...] = ()
    force_exit_symbols: tuple[str, ...] = ()


def compose_risk_decision(
    *,
    checks: tuple[RestrictionEvaluation, ...],
    limit_constraints: tuple[LimitConstraint, ...] = (),
    force_exit_symbols: tuple[str, ...] = (),
) -> ComposedRiskDecision:
    """Compose the deterministic risk outcome from check results and limits."""

    if force_exit_symbols:
        return ComposedRiskDecision(
            decision="FORCE_EXIT",
            reasons=("force_exit_required",),
            force_exit_symbols=force_exit_symbols,
        )

    rejection_reasons = tuple(
        reason
        for check in checks
        if not check.allowed
        for reason in check.reason_codes
    )
    if rejection_reasons:
        return ComposedRiskDecision(decision="REJECT", reasons=rejection_reasons)

    if limit_constraints:
        return ComposedRiskDecision(
            decision="APPROVE_WITH_LIMITS",
            reasons=("limits_required",),
            limit_constraints=limit_constraints,
        )

    return ComposedRiskDecision(decision="APPROVE", reasons=("all_checks_passed",))


__all__ = [
    "ComposedRiskDecision",
    "compose_risk_decision",
]
