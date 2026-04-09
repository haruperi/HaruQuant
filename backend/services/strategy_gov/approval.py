"""Promotion approval routing."""

from __future__ import annotations

from dataclasses import dataclass

from .models import StrategyLifecycleState


PROMOTION_APPROVAL_ROLES: dict[StrategyLifecycleState, tuple[str, ...]] = {
    StrategyLifecycleState.BACKTEST_QUALIFIED: ("strategy_owner",),
    StrategyLifecycleState.ROBUSTNESS_QUALIFIED: ("strategy_owner", "risk_manager"),
    StrategyLifecycleState.PAPER_APPROVED: ("risk_manager", "compliance"),
    StrategyLifecycleState.LIVE_LIMITED: ("risk_manager", "compliance"),
    StrategyLifecycleState.LIVE_PRODUCTION: ("risk_manager", "compliance"),
    StrategyLifecycleState.SUSPENDED: ("risk_manager",),
    StrategyLifecycleState.RETIRED: ("risk_manager", "compliance"),
}


@dataclass(frozen=True)
class PromotionApprovalRoute:
    target_state: StrategyLifecycleState
    required_roles: tuple[str, ...]
    required_count: int


def route_promotion_approval(
    *,
    target_state: StrategyLifecycleState,
) -> PromotionApprovalRoute:
    """Resolve the required promotion approver roles for a lifecycle target."""

    required_roles = PROMOTION_APPROVAL_ROLES.get(target_state, ("strategy_owner",))
    return PromotionApprovalRoute(
        target_state=target_state,
        required_roles=required_roles,
        required_count=len(required_roles),
    )
