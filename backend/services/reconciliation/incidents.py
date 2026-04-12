"""Incident raising for unresolved reconciliation divergence."""

from __future__ import annotations

import json
from pathlib import Path

from backend.common import generate_id
from backend.data.database import IncidentRecord, WorkflowRepository

from .comparison import ReconciliationComparison, ReconciliationResultState


class ReconciliationIncidentService:
    """Raises operator-visible incidents for unresolved broker divergence."""

    def __init__(self, db_path: str | Path) -> None:
        self.repository = WorkflowRepository(db_path)

    def raise_for_unresolved_divergence(
        self,
        *,
        execution_intent_id: str,
        comparison: ReconciliationComparison,
    ) -> IncidentRecord:
        if comparison.result_state is not ReconciliationResultState.CONFLICTING:
            raise ValueError("incident raising requires conflicting reconciliation state")

        metadata_json = json.dumps(
            {
                "execution_intent_id": execution_intent_id,
                "client_order_id": comparison.local_truth.client_order_id,
                "reason_codes": comparison.reason_codes,
                "local_status": comparison.local_truth.status,
                "receipt_status": comparison.local_truth.receipt_status,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        summary = (
            f"Unresolved broker/local divergence for execution intent {execution_intent_id}"
        )
        return self.repository.create_incident(
            incident_id=generate_id("incident"),
            severity="INCIDENT",
            state="OPEN",
            alert_type="BROKER_STATE_DIVERGENCE",
            source="reconciliation_engine",
            summary=summary,
            recommended_action="Hold retries and review broker/account state before further execution.",
            metadata_json=metadata_json,
        )
