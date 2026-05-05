from __future__ import annotations

from haruquant.execution import (
    BrokerTruthSnapshot,
    LocalExecutionTruth,
    ReconciliationComparison,
    ReconciliationResultState,
    evaluate_retry_guard,
)


def test_broker_ack_delay_chaos_scenario_blocks_blind_retry() -> None:
    comparison = ReconciliationComparison(
        local_truth=LocalExecutionTruth(
            execution_intent_id="exec_001",
            status="SENT",
            client_order_id="client_001",
            broker_order_id=None,
            broker_deal_id=None,
            receipt_status=None,
            authoritative_state=None,
        ),
        broker_truth=BrokerTruthSnapshot(
            client_order_id="client_001",
            account_state={},
            matched_order=None,
            matched_position=None,
        ),
        result_state=ReconciliationResultState.ABSENT,
        conflict_flag=False,
        reason_codes=("broker_state_absent",),
    )

    decision = evaluate_retry_guard(comparison)

    assert decision.allow_retry is False
    assert decision.reason_codes == ("retry_blocked_ack_delay_pending_reconciliation",)
