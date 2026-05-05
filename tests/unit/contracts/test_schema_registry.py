from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import SchemaRegistryRecord


def test_schema_registry_record_accepts_required_fields():
    record = SchemaRegistryRecord(
        contract_type="WorkflowIntent",
        schema_version="1.0.0",
        semantic_version="1.0.0",
        status="active",
        effective_from=datetime(2026, 4, 8, 10, 0, 0, tzinfo=timezone.utc),
        compatibility_policy="major-version compatibility",
        payload_hash="sha256:123abc",
        json_schema_ref="contracts/workflow_intent/schema.json",
        pydantic_model_ref="contracts.workflow_intent.model.WorkflowIntent",
        owning_domain_team="platform",
        changelog_summary="Initial active version.",
    )

    assert record.contract_type == "WorkflowIntent"
    assert record.status == "active"
    assert record.deprecated_from is None


def test_schema_registry_record_rejects_invalid_status():
    with pytest.raises(ValidationError):
        SchemaRegistryRecord(
            contract_type="WorkflowIntent",
            schema_version="1.0.0",
            semantic_version="1.0.0",
            status="published",
            effective_from=datetime(2026, 4, 8, 10, 0, 0, tzinfo=timezone.utc),
            compatibility_policy="major-version compatibility",
            payload_hash="sha256:123abc",
            json_schema_ref="contracts/workflow_intent/schema.json",
            pydantic_model_ref="contracts.workflow_intent.model.WorkflowIntent",
            owning_domain_team="platform",
            changelog_summary="Initial active version.",
        )
