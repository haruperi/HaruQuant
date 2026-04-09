"""Strategy operating-envelope updates after promotion."""

from __future__ import annotations

from dataclasses import dataclass

from .models import StrategyLifecycleState


@dataclass(frozen=True)
class StrategyOperatingEnvelope:
    lifecycle_state: StrategyLifecycleState
    operating_mode: str
    live_trading_allowed: bool
    approval_required: bool
    autonomy_ceiling: str


def update_operating_envelope_for_promotion(
    *,
    lifecycle_state: StrategyLifecycleState,
) -> StrategyOperatingEnvelope:
    """Resolve the operating envelope unlocked by the promoted lifecycle state."""

    if lifecycle_state is StrategyLifecycleState.PAPER_APPROVED:
        return StrategyOperatingEnvelope(
            lifecycle_state=lifecycle_state,
            operating_mode="MODE-002",
            live_trading_allowed=False,
            approval_required=False,
            autonomy_ceiling="paper_execution",
        )
    if lifecycle_state is StrategyLifecycleState.LIVE_LIMITED:
        return StrategyOperatingEnvelope(
            lifecycle_state=lifecycle_state,
            operating_mode="MODE-003",
            live_trading_allowed=True,
            approval_required=True,
            autonomy_ceiling="human_approved_live",
        )
    if lifecycle_state is StrategyLifecycleState.LIVE_PRODUCTION:
        return StrategyOperatingEnvelope(
            lifecycle_state=lifecycle_state,
            operating_mode="MODE-004",
            live_trading_allowed=True,
            approval_required=False,
            autonomy_ceiling="bounded_autonomous_live",
        )
    return StrategyOperatingEnvelope(
        lifecycle_state=lifecycle_state,
        operating_mode="MODE-001",
        live_trading_allowed=False,
        approval_required=True,
        autonomy_ceiling="advisory_only",
    )
