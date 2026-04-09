from __future__ import annotations

from backend.services import StrategyLifecycleState, route_promotion_approval


def test_route_promotion_approval_returns_required_roles_for_live_targets() -> None:
    route = route_promotion_approval(target_state=StrategyLifecycleState.LIVE_LIMITED)

    assert route.required_roles == ("risk_manager", "compliance")
    assert route.required_count == 2


def test_route_promotion_approval_defaults_to_strategy_owner_for_early_stage() -> None:
    route = route_promotion_approval(target_state=StrategyLifecycleState.BACKTEST_QUALIFIED)

    assert route.required_roles == ("strategy_owner",)
    assert route.required_count == 1
