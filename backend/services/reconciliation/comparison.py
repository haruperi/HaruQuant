"""Local-vs-broker truth comparison for reconciliation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from backend.data.database import ExecutionIntentRecord, ExecutionReceiptRecord

from .broker_truth import BrokerTruthSnapshot

_IN_FLIGHT_LOCAL_STATUSES = frozenset(
    {
        "EXECUTION_PENDING",
        "PENDING",
        "SENT",
        "ACKNOWLEDGED",
        "PARTIALLY_FILLED",
    }
)
_EXECUTION_PRESENT_RECEIPT_STATUSES = frozenset(
    {
        "accepted",
        "queued",
        "partially_filled",
        "filled",
    }
)
_FINAL_LOCAL_FAILURE_STATUSES = frozenset({"EXECUTION_FAILED", "FAILED", "CANCELLED", "CLOSED"})


class ReconciliationResultState(StrEnum):
    MATCHED = "MATCHED"
    ABSENT = "ABSENT"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True)
class LocalExecutionTruth:
    execution_intent_id: str
    status: str
    client_order_id: str | None
    receipt_status: str | None
    broker_order_id: str | None
    broker_deal_id: str | None
    authoritative_state: dict[str, object] | None


@dataclass(frozen=True)
class ReconciliationComparison:
    result_state: ReconciliationResultState
    conflict_flag: bool
    reason_codes: tuple[str, ...]
    local_truth: LocalExecutionTruth
    broker_truth: BrokerTruthSnapshot


def build_local_execution_truth(
    intent: ExecutionIntentRecord,
    latest_receipt: ExecutionReceiptRecord | None = None,
) -> LocalExecutionTruth:
    authoritative_state: dict[str, object] | None = None
    if latest_receipt is not None and latest_receipt.authoritative_state.strip():
        authoritative_state = json.loads(latest_receipt.authoritative_state)
    return LocalExecutionTruth(
        execution_intent_id=intent.execution_intent_id,
        status=intent.status,
        client_order_id=intent.client_order_id,
        receipt_status=None if latest_receipt is None else latest_receipt.receipt_status,
        broker_order_id=None if latest_receipt is None else latest_receipt.broker_order_id,
        broker_deal_id=None if latest_receipt is None else latest_receipt.broker_deal_id,
        authoritative_state=authoritative_state,
    )


def compare_execution_truth(
    *,
    local_truth: LocalExecutionTruth,
    broker_truth: BrokerTruthSnapshot,
) -> ReconciliationComparison:
    broker_present = broker_truth.matched_order is not None or broker_truth.matched_position is not None
    reason_codes: list[str] = []

    if broker_present:
        if local_truth.status in _FINAL_LOCAL_FAILURE_STATUSES:
            reason_codes.append("broker_present_local_final_failure")
            return ReconciliationComparison(
                result_state=ReconciliationResultState.CONFLICTING,
                conflict_flag=True,
                reason_codes=tuple(reason_codes),
                local_truth=local_truth,
                broker_truth=broker_truth,
            )
        broker_order_id = None
        if broker_truth.matched_order is not None:
            broker_order_id = str(
                broker_truth.matched_order.get("order")
                or broker_truth.matched_order.get("order_id")
                or broker_truth.matched_order.get("ticket")
                or ""
            ) or None
        if (
            local_truth.broker_order_id is not None
            and broker_order_id is not None
            and local_truth.broker_order_id != broker_order_id
        ):
            reason_codes.append("broker_order_id_mismatch")
            return ReconciliationComparison(
                result_state=ReconciliationResultState.CONFLICTING,
                conflict_flag=True,
                reason_codes=tuple(reason_codes),
                local_truth=local_truth,
                broker_truth=broker_truth,
            )

        reason_codes.append("broker_state_confirmed")
        return ReconciliationComparison(
            result_state=ReconciliationResultState.MATCHED,
            conflict_flag=False,
            reason_codes=tuple(reason_codes),
            local_truth=local_truth,
            broker_truth=broker_truth,
        )

    if local_truth.receipt_status in {"filled", "partially_filled"}:
        reason_codes.append("broker_absent_local_fill_recorded")
        return ReconciliationComparison(
            result_state=ReconciliationResultState.CONFLICTING,
            conflict_flag=True,
            reason_codes=tuple(reason_codes),
            local_truth=local_truth,
            broker_truth=broker_truth,
        )

    if local_truth.status in _IN_FLIGHT_LOCAL_STATUSES or local_truth.receipt_status in _EXECUTION_PRESENT_RECEIPT_STATUSES:
        reason_codes.append("broker_state_absent")
        return ReconciliationComparison(
            result_state=ReconciliationResultState.ABSENT,
            conflict_flag=False,
            reason_codes=tuple(reason_codes),
            local_truth=local_truth,
            broker_truth=broker_truth,
        )

    reason_codes.append("broker_absent_local_inconsistent")
    return ReconciliationComparison(
        result_state=ReconciliationResultState.CONFLICTING,
        conflict_flag=True,
        reason_codes=tuple(reason_codes),
        local_truth=local_truth,
        broker_truth=broker_truth,
    )
