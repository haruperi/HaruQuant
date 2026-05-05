from __future__ import annotations

from haruquant.execution import (
    BrokerTruthSnapshot,
    LocalExecutionTruth,
    ReconciliationComparison,
    ReconciliationResultState,
    evaluate_retry_guard,
)


def _comparison(
    *,
    result_state: ReconciliationResultState,
    status: str,
    receipt_status: str | None = None,
) -> ReconciliationComparison:
    return ReconciliationComparison(
        result_state=result_state,
        conflict_flag=result_state is ReconciliationResultState.CONFLICTING,
        reason_codes=("test",),
        local_truth=LocalExecutionTruth(
            execution_intent_id="exec_001",
            status=status,
            client_order_id="client_001",
            receipt_status=receipt_status,
            broker_order_id=None,
            broker_deal_id=None,
            authoritative_state=None,
        ),
        broker_truth=BrokerTruthSnapshot(
            client_order_id="client_001",
            account_state={"login": 12345},
            matched_order=None,
            matched_position=None,
        ),
    )


def test_retry_guard_blocks_absent_state_during_ack_delay() -> None:
    decision = evaluate_retry_guard(
        _comparison(
            result_state=ReconciliationResultState.ABSENT,
            status="ACKNOWLEDGED",
        )
    )

    assert decision.allow_retry is False
    assert decision.reason_codes == ("retry_blocked_ack_delay_pending_reconciliation",)


def test_retry_guard_blocks_absent_state_with_pending_receipt() -> None:
    decision = evaluate_retry_guard(
        _comparison(
            result_state=ReconciliationResultState.ABSENT,
            status="SENT",
            receipt_status="accepted",
        )
    )

    assert decision.allow_retry is False


def test_retry_guard_blocks_conflicting_state() -> None:
    decision = evaluate_retry_guard(
        _comparison(
            result_state=ReconciliationResultState.CONFLICTING,
            status="PARTIALLY_FILLED",
            receipt_status="filled",
        )
    )

    assert decision.allow_retry is False
    assert decision.reason_codes == ("retry_blocked_conflicting_broker_state",)


def test_retry_guard_allows_retry_after_clean_match() -> None:
    decision = evaluate_retry_guard(
        _comparison(
            result_state=ReconciliationResultState.MATCHED,
            status="SENT",
            receipt_status="accepted",
        )
    )

    assert decision.allow_retry is True
