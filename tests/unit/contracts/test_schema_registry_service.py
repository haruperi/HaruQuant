from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.contracts import (
    SchemaRegistryRecord,
    SchemaRegistryResolutionError,
    SchemaRegistryService,
)


def _record(
    contract_type: str,
    schema_version: str,
    *,
    semantic_version: str,
    status: str,
    effective_from: datetime,
    deprecated_from: datetime | None = None,
) -> SchemaRegistryRecord:
    return SchemaRegistryRecord(
        contract_type=contract_type,
        schema_version=schema_version,
        semantic_version=semantic_version,
        status=status,
        effective_from=effective_from,
        deprecated_from=deprecated_from,
        compatibility_policy="major-version compatibility",
        payload_hash=f"sha256:{schema_version}",
        json_schema_ref=f"backend/contracts/{contract_type.lower()}/schema.json",
        pydantic_model_ref=f"backend.contracts.{contract_type.lower()}.model.{contract_type}",
        owning_domain_team="platform",
        changelog_summary=f"{schema_version} status {status}",
    )


def test_schema_registry_service_resolves_active_version():
    service = SchemaRegistryService(
        [
            _record(
                "WorkflowIntent",
                "1.0.0",
                semantic_version="1.0.0",
                status="deprecated",
                effective_from=datetime(2026, 4, 1, tzinfo=timezone.utc),
                deprecated_from=datetime(2026, 4, 10, tzinfo=timezone.utc),
            ),
            _record(
                "WorkflowIntent",
                "1.1.0",
                semantic_version="1.1.0",
                status="active",
                effective_from=datetime(2026, 4, 10, tzinfo=timezone.utc),
            ),
        ]
    )

    active = service.get_active_version(
        "WorkflowIntent",
        at=datetime(2026, 4, 11, tzinfo=timezone.utc),
    )

    assert active.schema_version == "1.1.0"


def test_schema_registry_service_returns_deprecated_versions():
    deprecated = _record(
        "WorkflowIntent",
        "1.0.0",
        semantic_version="1.0.0",
        status="deprecated",
        effective_from=datetime(2026, 4, 1, tzinfo=timezone.utc),
        deprecated_from=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    active = _record(
        "WorkflowIntent",
        "1.1.0",
        semantic_version="1.1.0",
        status="active",
        effective_from=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    service = SchemaRegistryService([deprecated, active])

    records = service.get_deprecated_versions("WorkflowIntent")

    assert records == [deprecated]


def test_schema_registry_service_raises_for_missing_active_version():
    service = SchemaRegistryService([])

    with pytest.raises(SchemaRegistryResolutionError):
        service.get_active_version("WorkflowIntent")
