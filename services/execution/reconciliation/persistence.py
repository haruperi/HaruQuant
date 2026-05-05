"""Persistence helpers for reconciliation runs."""

from __future__ import annotations

import json
from pathlib import Path

from data.database import ExecutionRepository, ReconciliationRunRecord

from .comparison import ReconciliationComparison


class ReconciliationPersistenceService:
    """Persist append-only reconciliation results."""

    def __init__(self, db_path: str | Path) -> None:
        self.repository = ExecutionRepository(db_path)

    def save(
        self,
        *,
        execution_intent_id: str,
        run_reason: str,
        comparison: ReconciliationComparison,
        incident_id: str | None = None,
        completed_at: str | None = None,
    ) -> ReconciliationRunRecord:
        broker_truth_json = json.dumps(
            {
                "client_order_id": comparison.broker_truth.client_order_id,
                "account_state": comparison.broker_truth.account_state,
                "matched_order": comparison.broker_truth.matched_order,
                "matched_position": comparison.broker_truth.matched_position,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        local_truth_json = json.dumps(
            {
                "execution_intent_id": comparison.local_truth.execution_intent_id,
                "status": comparison.local_truth.status,
                "client_order_id": comparison.local_truth.client_order_id,
                "receipt_status": comparison.local_truth.receipt_status,
                "broker_order_id": comparison.local_truth.broker_order_id,
                "broker_deal_id": comparison.local_truth.broker_deal_id,
                "authoritative_state": comparison.local_truth.authoritative_state,
                "reason_codes": comparison.reason_codes,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return self.repository.add_reconciliation_run(
            execution_intent_id=execution_intent_id,
            run_reason=run_reason,
            result_state=comparison.result_state.value,
            broker_truth_json=broker_truth_json,
            local_truth_json=local_truth_json,
            conflict_flag=1 if comparison.conflict_flag else 0,
            incident_id=incident_id,
            completed_at=completed_at,
        )
