"""Restriction and compatibility evaluators for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time


@dataclass(frozen=True)
class RestrictionEvaluation:
    """Simple allow/deny result with deterministic reason codes."""

    allowed: bool
    reason_codes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def evaluate_regime_restriction(
    *,
    current_regime: str,
    allowed_regimes: tuple[str, ...],
) -> RestrictionEvaluation:
    """Allow action only when the current regime is explicitly permitted."""

    if current_regime in allowed_regimes:
        return RestrictionEvaluation(allowed=True, metadata={"current_regime": current_regime})
    return RestrictionEvaluation(
        allowed=False,
        reason_codes=("regime_not_allowed",),
        metadata={"current_regime": current_regime, "allowed_regimes": allowed_regimes},
    )


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


__all__ = [
    "RestrictionEvaluation",
    "evaluate_regime_restriction",
]
