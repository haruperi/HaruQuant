"""Restriction and compatibility evaluators for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time

from backend.common.logger import logger


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


def evaluate_session_restrictions(
    *,
    current_time: datetime,
    allowed_window: tuple[str, str],
    blackout_windows: tuple[tuple[str, str], ...] = (),
) -> RestrictionEvaluation:
    """Check session allow window and blackout overlap for the current time."""

    current_clock_time = current_time.time().replace(second=0, microsecond=0)
    start_time = _parse_hhmm(allowed_window[0])
    end_time = _parse_hhmm(allowed_window[1])
    if not (start_time <= current_clock_time <= end_time):
        return RestrictionEvaluation(
            allowed=False,
            reason_codes=("outside_session_window",),
            metadata={"allowed_window": allowed_window},
        )

    for blackout_start, blackout_end in blackout_windows:
        if _parse_hhmm(blackout_start) <= current_clock_time <= _parse_hhmm(blackout_end):
            return RestrictionEvaluation(
                allowed=False,
                reason_codes=("active_blackout_window",),
                metadata={"blackout_window": (blackout_start, blackout_end)},
            )

    return RestrictionEvaluation(
        allowed=True,
        metadata={"allowed_window": allowed_window, "blackout_windows": blackout_windows},
    )


def evaluate_spread_slippage_precheck(
    *,
    spread_points: float,
    max_spread_points: float,
    expected_slippage_points: float,
    max_slippage_points: float,
) -> RestrictionEvaluation:
    """Block entries when spread or expected slippage exceed configured limits."""

    reasons: list[str] = []
    if spread_points > max_spread_points:
        reasons.append("spread_threshold_exceeded")
    if expected_slippage_points > max_slippage_points:
        reasons.append("slippage_threshold_exceeded")

    return RestrictionEvaluation(
        allowed=not reasons,
        reason_codes=tuple(reasons),
        metadata={
            "spread_points": spread_points,
            "max_spread_points": max_spread_points,
            "expected_slippage_points": expected_slippage_points,
            "max_slippage_points": max_slippage_points,
        },
    )


def evaluate_operating_mode_compatibility(
    *,
    workflow_operating_mode: str,
    allowed_operating_modes: tuple[str, ...],
) -> RestrictionEvaluation:
    """Check whether the current workflow mode is permitted for the action."""

    if workflow_operating_mode in allowed_operating_modes:
        return RestrictionEvaluation(
            allowed=True,
            metadata={"workflow_operating_mode": workflow_operating_mode},
        )
    return RestrictionEvaluation(
        allowed=False,
        reason_codes=("operating_mode_not_allowed",),
        metadata={
            "workflow_operating_mode": workflow_operating_mode,
            "allowed_operating_modes": allowed_operating_modes,
        },
    )


def evaluate_compliance_profile_compatibility(
    *,
    active_compliance_profile_id: str,
    allowed_compliance_profile_ids: tuple[str, ...],
) -> RestrictionEvaluation:
    """Check whether the active compliance profile is permitted for the action."""

    if active_compliance_profile_id in allowed_compliance_profile_ids:
        return RestrictionEvaluation(
            allowed=True,
            metadata={"active_compliance_profile_id": active_compliance_profile_id},
        )
    return RestrictionEvaluation(
        allowed=False,
        reason_codes=("compliance_profile_not_allowed",),
        metadata={
            "active_compliance_profile_id": active_compliance_profile_id,
            "allowed_compliance_profile_ids": allowed_compliance_profile_ids,
        },
    )


__all__ = [
    "RestrictionEvaluation",
    "evaluate_regime_restriction",
    "evaluate_session_restrictions",
    "evaluate_spread_slippage_precheck",
    "evaluate_operating_mode_compatibility",
    "evaluate_compliance_profile_compatibility",
]
