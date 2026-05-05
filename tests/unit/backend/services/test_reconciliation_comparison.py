from __future__ import annotations

from data.database import ExecutionIntentRecord, ExecutionReceiptRecord
from haruquant.execution import (
    BrokerTruthSnapshot,
    ReconciliationResultState,
    build_local_execution_truth,
    compare_execution_truth,
)


def _intent(*, status: str, client_order_id: str = "client_001") -> ExecutionIntentRecord:
    return ExecutionIntentRecord(
        execution_intent_id="exec_001",
        workflow_id="wf_001",
        proposal_id="prop_001",
        risk_decision_id="risk_dec_001",
        action_type="open_position",
        symbol="EURUSD",
        side="buy",
        order_type="limit",
        size_json='{"units":1000}',
        price_params_json="{}",
        sl_tp_params_json="{}",
        idempotency_key="idem_001",
        client_order_id=client_order_id,
        status=status,
        expiry_at=None,
        pre_send_validation_snapshot_ref=None,
        created_at="2026-04-09T10:00:00Z",
        updated_at="2026-04-09T10:00:00Z",
    )


def _receipt(*, status: str, broker_order_id: str | None = None) -> ExecutionReceiptRecord:
    return ExecutionReceiptRecord(
        receipt_id="rcpt_001",
        execution_intent_id="exec_001",
        broker="mt5",
        broker_order_id=broker_order_id,
        broker_deal_id=None,
        receipt_status=status,
        requested_price=1.1,
        fill_price=1.1001,
        fill_qty=1000.0,
        spread_points=None,
        slippage_points=None,
        slippage_bps=None,
        raw_receipt_ref=None,
        broker_message=None,
        broker_retcode=None,
        authoritative_state='{"position_state":"open"}',
        received_at="2026-04-09T10:00:01Z",
    )


def _broker_truth(
    *,
    order: dict[str, object] | None = None,
    position: dict[str, object] | None = None,
) -> BrokerTruthSnapshot:
    return BrokerTruthSnapshot(
        client_order_id="client_001",
        account_state={"login": 12345},
        matched_order=order,
        matched_position=position,
    )


def test_compare_execution_truth_classifies_confirmed_broker_match() -> None:
    local_truth = build_local_execution_truth(
        _intent(status="SENT"),
        _receipt(status="accepted", broker_order_id="401"),
    )

    comparison = compare_execution_truth(
        local_truth=local_truth,
        broker_truth=_broker_truth(order={"ticket": 401, "external_id": "client_001"}),
    )

    assert comparison.result_state == ReconciliationResultState.MATCHED
    assert comparison.conflict_flag is False


def test_compare_execution_truth_classifies_absent_when_broker_has_no_open_state() -> None:
    local_truth = build_local_execution_truth(_intent(status="ACKNOWLEDGED"))

    comparison = compare_execution_truth(
        local_truth=local_truth,
        broker_truth=_broker_truth(),
    )

    assert comparison.result_state == ReconciliationResultState.ABSENT
    assert comparison.conflict_flag is False


def test_compare_execution_truth_classifies_conflict_for_missing_broker_fill() -> None:
    local_truth = build_local_execution_truth(
        _intent(status="PARTIALLY_FILLED"),
        _receipt(status="filled", broker_order_id="401"),
    )

    comparison = compare_execution_truth(
        local_truth=local_truth,
        broker_truth=_broker_truth(),
    )

    assert comparison.result_state == ReconciliationResultState.CONFLICTING
    assert comparison.conflict_flag is True
