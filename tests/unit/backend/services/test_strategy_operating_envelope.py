from __future__ import annotations

from services.strategy.governance import StrategyLifecycleState, update_operating_envelope_for_promotion


def test_update_operating_envelope_for_live_limited_requires_human_approval() -> None:
    envelope = update_operating_envelope_for_promotion(
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
    )

    assert envelope.operating_mode == "MODE-003"
    assert envelope.live_trading_allowed is True
    assert envelope.approval_required is True


def test_update_operating_envelope_for_paper_keeps_live_disabled() -> None:
    envelope = update_operating_envelope_for_promotion(
        lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
    )

    assert envelope.operating_mode == "MODE-002"
    assert envelope.live_trading_allowed is False
