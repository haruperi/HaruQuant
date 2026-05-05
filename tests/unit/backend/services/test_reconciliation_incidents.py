from __future__ import annotations

from pathlib import Path

import pytest

from data.database import apply_pending_migrations, default_migrations_dir
from haruquant.execution import (
    BrokerTruthSnapshot,
    LocalExecutionTruth,
    ReconciliationComparison,
    ReconciliationIncidentService,
    ReconciliationResultState,
)


def _conflicting_comparison() -> ReconciliationComparison:
    return ReconciliationComparison(
        result_state=ReconciliationResultState.CONFLICTING,
        conflict_flag=True,
        reason_codes=("broker_absent_local_fill_recorded",),
        local_truth=LocalExecutionTruth(
            execution_intent_id="exec_001",
            status="PARTIALLY_FILLED",
            client_order_id="client_001",
            receipt_status="filled",
            broker_order_id="401",
            broker_deal_id=None,
            authoritative_state={"position_state": "open"},
        ),
        broker_truth=BrokerTruthSnapshot(
            client_order_id="client_001",
            account_state={"login": 12345},
            matched_order=None,
            matched_position=None,
        ),
    )


def test_reconciliation_incident_service_creates_incident_for_unresolved_divergence(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = ReconciliationIncidentService(database_path)

    incident = service.raise_for_unresolved_divergence(
        execution_intent_id="exec_001",
        comparison=_conflicting_comparison(),
    )

    assert incident.state == "OPEN"
    assert incident.severity == "INCIDENT"
    assert incident.alert_type == "BROKER_STATE_DIVERGENCE"
    assert '"execution_intent_id":"exec_001"' in incident.metadata_json


def test_reconciliation_incident_service_rejects_non_conflicting_state(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = ReconciliationIncidentService(database_path)

    comparison = _conflicting_comparison()
    comparison = ReconciliationComparison(
        result_state=ReconciliationResultState.MATCHED,
        conflict_flag=False,
        reason_codes=comparison.reason_codes,
        local_truth=comparison.local_truth,
        broker_truth=comparison.broker_truth,
    )

    with pytest.raises(ValueError, match="conflicting reconciliation state"):
        service.raise_for_unresolved_divergence(
            execution_intent_id="exec_001",
            comparison=comparison,
        )
