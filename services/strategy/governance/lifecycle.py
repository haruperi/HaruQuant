"""Strategy lifecycle transition validation."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils import ErrorDescriptor, PolicyError

from .models import StrategyLifecycleState


STRATEGY_LIFECYCLE_TRANSITIONS: dict[StrategyLifecycleState, frozenset[StrategyLifecycleState]] = {
    StrategyLifecycleState.RESEARCH: frozenset({StrategyLifecycleState.BACKTEST_QUALIFIED}),
    StrategyLifecycleState.BACKTEST_QUALIFIED: frozenset({StrategyLifecycleState.ROBUSTNESS_QUALIFIED}),
    StrategyLifecycleState.ROBUSTNESS_QUALIFIED: frozenset({StrategyLifecycleState.PAPER_APPROVED}),
    StrategyLifecycleState.PAPER_APPROVED: frozenset(
        {StrategyLifecycleState.LIVE_LIMITED, StrategyLifecycleState.SUSPENDED}
    ),
    StrategyLifecycleState.LIVE_LIMITED: frozenset(
        {StrategyLifecycleState.LIVE_PRODUCTION, StrategyLifecycleState.SUSPENDED}
    ),
    StrategyLifecycleState.LIVE_PRODUCTION: frozenset({StrategyLifecycleState.SUSPENDED}),
    StrategyLifecycleState.SUSPENDED: frozenset(
        {StrategyLifecycleState.PAPER_APPROVED, StrategyLifecycleState.LIVE_LIMITED, StrategyLifecycleState.RETIRED}
    ),
    StrategyLifecycleState.RETIRED: frozenset(),
}

_STRATEGY_LIFECYCLE_TRANSITION_NOT_ALLOWED = ErrorDescriptor(
    code=4041,
    name="STRATEGY_LIFECYCLE_TRANSITION_NOT_ALLOWED",
    message="Strategy lifecycle transition is not allowed.",
    domain="strategy_governance",
)


@dataclass(frozen=True)
class StrategyLifecycleTransition:
    previous_state: StrategyLifecycleState
    next_state: StrategyLifecycleState


class StrategyLifecycleTransitionValidator:
    """Validate deterministic lifecycle transitions for strategy governance."""

    def validate(
        self,
        *,
        previous_state: StrategyLifecycleState,
        next_state: StrategyLifecycleState,
    ) -> StrategyLifecycleTransition:
        if next_state not in STRATEGY_LIFECYCLE_TRANSITIONS[previous_state]:
            raise PolicyError(
                _STRATEGY_LIFECYCLE_TRANSITION_NOT_ALLOWED,
                "Strategy lifecycle transition is not allowed: "
                f"{previous_state.value} -> {next_state.value}.",
            )
        return StrategyLifecycleTransition(
            previous_state=previous_state,
            next_state=next_state,
        )

