from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.contracts import (
    ContractValidationError,
    SchemaRegistryRecord,
    SchemaRegistryService,
    validate_contract_payload,
)


def _registry() -> SchemaRegistryService:
    record = SchemaRegistryRecord(
        contract_type="WorkflowIntent",
        schema_version="1.0.0",
        semantic_version="1.0.0",
        status="active",
        effective_from=datetime(2026, 4, 8, tzinfo=timezone.utc),
        compatibility_policy="major-version compatibility",
        payload_hash="sha256:123abc",
        json_schema_ref="backend/contracts/workflow_intent/schema.json",
        pydantic_model_ref="backend.contracts.workflow_intent.model.WorkflowIntent",
        owning_domain_team="platform",
        changelog_summary="Initial active version.",
    )
    return SchemaRegistryService([record])


def test_validate_contract_payload_accepts_registered_contract():
    payload = {
        "schema_version": "1.0.0",
        "contract_type": "WorkflowIntent",
        "workflow_id": "wf_01",
        "correlation_id": "corr_01",
        "causation_id": "evt_01",
        "timestamp_utc": "2026-04-08T10:15:30Z",
        "originator": {"type": "user", "id": "user_123"},
        "environment": "paper",
        "operating_mode": "MODE-001",
        "payload": {
            "objective": "Review EURUSD trade idea",
            "workflow_type": "trade_review",
            "trigger_type": "user_action",
            "requested_scope": {"symbol_group": ["EURUSD"]},
        },
    }

    model = validate_contract_payload(payload, _registry())

    assert model.contract_type == "WorkflowIntent"


def test_validate_contract_payload_rejects_unregistered_version():
    payload = {
        "schema_version": "9.9.9",
        "contract_type": "WorkflowIntent",
        "workflow_id": "wf_01",
        "correlation_id": "corr_01",
        "causation_id": "evt_01",
        "timestamp_utc": "2026-04-08T10:15:30Z",
        "originator": {"type": "user", "id": "user_123"},
        "environment": "paper",
        "operating_mode": "MODE-001",
        "payload": {},
    }

    with pytest.raises(ContractValidationError):
        validate_contract_payload(payload, _registry())


def test_validate_contract_payload_rejects_malformed_registered_contract():
    payload = {
        "schema_version": "1.0.0",
        "contract_type": "WorkflowIntent",
        "workflow_id": "wf_01",
        "correlation_id": "corr_01",
        "causation_id": "evt_01",
        "timestamp_utc": "2026-04-08T10:15:30Z",
        "originator": {"type": "user", "id": "user_123"},
        "environment": "paper",
        "operating_mode": "MODE-001",
        "payload": {
            "workflow_type": "trade_review",
            "trigger_type": "user_action",
            "requested_scope": {"symbol_group": ["EURUSD"]},
        },
    }

    with pytest.raises(ContractValidationError):
        validate_contract_payload(payload, _registry())
