from __future__ import annotations

from haruquant.strategy import SuspensionTriggerRequest, evaluate_suspension_triggers


def test_evaluate_suspension_triggers_returns_triggered_when_thresholds_breach() -> None:
    decision = evaluate_suspension_triggers(
        SuspensionTriggerRequest(
            drawdown_ratio=0.22,
            unresolved_incident_count=2,
            policy_breach_count=1,
        )
    )

    assert decision.triggered is True
    assert decision.reason_codes == (
        "drawdown_threshold_breached",
        "incident_threshold_breached",
        "policy_breach_threshold_exceeded",
    )


def test_evaluate_suspension_triggers_returns_clear_when_within_thresholds() -> None:
    decision = evaluate_suspension_triggers(
        SuspensionTriggerRequest(
            drawdown_ratio=0.05,
            unresolved_incident_count=0,
            policy_breach_count=0,
        )
    )

    assert decision.triggered is False
    assert decision.reason_codes == ()
