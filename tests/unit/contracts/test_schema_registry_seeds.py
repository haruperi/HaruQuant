from __future__ import annotations

from backend_retiring.contracts import (
    INITIAL_SCHEMA_SEEDS,
    SchemaRegistryService,
    load_initial_schema_registry_seeds,
)


def test_schema_registry_seeds_cover_all_initial_contract_types():
    records = load_initial_schema_registry_seeds()

    assert len(records) == len(INITIAL_SCHEMA_SEEDS)
    assert {record.contract_type for record in records} == {
        contract_type for contract_type, _ in INITIAL_SCHEMA_SEEDS
    }


def test_schema_registry_seeds_are_active_initial_versions():
    records = load_initial_schema_registry_seeds()

    assert all(record.status == "active" for record in records)
    assert all(record.schema_version == "1.0.0" for record in records)


def test_schema_registry_seeds_work_with_version_resolution():
    service = SchemaRegistryService(load_initial_schema_registry_seeds())

    record = service.get_version("WorkflowIntent", "1.0.0")

    assert record.contract_type == "WorkflowIntent"
    assert record.pydantic_model_ref.endswith(".WorkflowIntent")
