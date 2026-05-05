from __future__ import annotations

from haruquant.strategy import (
    StrategyLifecycleState,
    update_operating_envelope_for_promotion,
)
from haruquant.risk import evaluate_operating_mode_compatibility


def test_live_entry_blocked_when_workflow_attempts_unsupported_autonomy_escalation() -> None:
    approved_envelope = update_operating_envelope_for_promotion(
        lifecycle_state=StrategyLifecycleState.LIVE_LIMITED,
    )
    attempted_execution_mode = "MODE-004"

    compatibility = evaluate_operating_mode_compatibility(
        workflow_operating_mode=attempted_execution_mode,
        allowed_operating_modes=(approved_envelope.operating_mode,),
    )

    assert approved_envelope.operating_mode == "MODE-003"
    assert approved_envelope.autonomy_ceiling == "human_approved_live"
    assert compatibility.allowed is False
    assert compatibility.reason_codes == ("operating_mode_not_allowed",)
