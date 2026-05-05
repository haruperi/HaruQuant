from __future__ import annotations

from datetime import datetime, timezone

from backend_retiring.contracts import (
    SCHEMA_REGISTRY_TABLE,
    SchemaRegistryRecord,
    SchemaRegistryRow,
    record_to_row,
    row_to_record,
)


def _sample_record() -> SchemaRegistryRecord:
    return SchemaRegistryRecord(
        contract_type="WorkflowIntent",
        schema_version="1.0.0",
        semantic_version="1.0.0",
        status="active",
        effective_from=datetime(2026, 4, 8, 10, 0, 0, tzinfo=timezone.utc),
        compatibility_policy="major-version compatibility",
        payload_hash="sha256:123abc",
        json_schema_ref="backend_retiring/contracts/workflow_intent/schema.json",
        pydantic_model_ref="backend_retiring.contracts.workflow_intent.model.WorkflowIntent",
        owning_domain_team="platform",
        changelog_summary="Initial active version.",
    )


def test_schema_registry_table_name_is_stable():
    assert SCHEMA_REGISTRY_TABLE == "schema_registry"


def test_record_to_row_preserves_registry_fields():
    row = record_to_row(_sample_record())

    assert isinstance(row, SchemaRegistryRow)
    assert row.contract_type == "WorkflowIntent"
    assert row.status == "active"


def test_row_to_record_round_trips_from_mapping():
    row = {
        "contract_type": "WorkflowIntent",
        "schema_version": "1.0.0",
        "semantic_version": "1.0.0",
        "status": "active",
        "effective_from": "2026-04-08T10:00:00Z",
        "deprecated_from": None,
        "compatibility_policy": "major-version compatibility",
        "payload_hash": "sha256:123abc",
        "json_schema_ref": "backend_retiring/contracts/workflow_intent/schema.json",
        "pydantic_model_ref": "backend_retiring.contracts.workflow_intent.model.WorkflowIntent",
        "owning_domain_team": "platform",
        "changelog_summary": "Initial active version.",
    }

    record = row_to_record(row)

    assert record.contract_type == "WorkflowIntent"
    assert record.status == "active"
