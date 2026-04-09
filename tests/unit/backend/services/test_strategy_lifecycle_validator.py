from __future__ import annotations

import pytest

from backend.services import (
    StrategyLifecycleState,
    StrategyLifecycleTransitionValidator,
)


def test_strategy_lifecycle_transition_validator_accepts_valid_path() -> None:
    transition = StrategyLifecycleTransitionValidator().validate(
        previous_state=StrategyLifecycleState.PAPER_APPROVED,
        next_state=StrategyLifecycleState.LIVE_LIMITED,
    )

    assert transition.previous_state is StrategyLifecycleState.PAPER_APPROVED
    assert transition.next_state is StrategyLifecycleState.LIVE_LIMITED


def test_strategy_lifecycle_transition_validator_rejects_invalid_jump() -> None:
    with pytest.raises(Exception):
        StrategyLifecycleTransitionValidator().validate(
            previous_state=StrategyLifecycleState.RESEARCH,
            next_state=StrategyLifecycleState.LIVE_LIMITED,
        )
