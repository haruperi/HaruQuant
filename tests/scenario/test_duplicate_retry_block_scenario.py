from __future__ import annotations

from haruquant.execution import (
    BrokerTruthSnapshot,
    LocalExecutionTruth,
    ReconciliationResultState,
    ReconciliationComparison,
    evaluate_retry_guard,
)


def test_duplicate_retry_blocked_until_reconciliation_completes() -> None:
    comparison = ReconciliationComparison(
        result_state=ReconciliationResultState.ABSENT,
        conflict_flag=False,
        reason_codes=("broker_state_absent",),
        local_truth=LocalExecutionTruth(
            execution_intent_id="exec_001",
            status="ACKNOWLEDGED",
            client_order_id="client_exec_001",
            receipt_status="accepted",
            broker_order_id=None,
            broker_deal_id=None,
            authoritative_state=None,
        ),
        broker_truth=BrokerTruthSnapshot(
            client_order_id="client_exec_001",
            account_state={"balance": 10000},
            matched_order=None,
            matched_position=None,
        ),
    )

    decision = evaluate_retry_guard(comparison)

    assert decision.allow_retry is False
    assert decision.reason_codes == ("retry_blocked_ack_delay_pending_reconciliation",)

