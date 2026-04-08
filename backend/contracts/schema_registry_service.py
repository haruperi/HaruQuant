"""Version resolution service for schema registry records."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from .schema_registry import SchemaRegistryRecord


class SchemaRegistryResolutionError(LookupError):
    """Raised when a schema registry lookup cannot be resolved."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SchemaRegistryService:
    """In-memory registry service for version lookup and resolution."""

    def __init__(self, records: Iterable[SchemaRegistryRecord]):
        self._by_contract_type: dict[str, list[SchemaRegistryRecord]] = defaultdict(list)
        for record in records:
            self._by_contract_type[record.contract_type].append(record)

        for record_list in self._by_contract_type.values():
            record_list.sort(key=lambda item: (item.effective_from, item.semantic_version))

    def list_versions(self, contract_type: str) -> list[SchemaRegistryRecord]:
        """Return all known versions for a contract type."""

        return list(self._by_contract_type.get(contract_type, []))

    def get_version(self, contract_type: str, schema_version: str) -> SchemaRegistryRecord:
        """Resolve one exact schema version for a contract type."""

        for record in self._by_contract_type.get(contract_type, []):
            if record.schema_version == schema_version:
                return record
        raise SchemaRegistryResolutionError(
            f"No schema version '{schema_version}' found for contract '{contract_type}'."
        )

    def get_active_version(
        self,
        contract_type: str,
        *,
        at: datetime | None = None,
    ) -> SchemaRegistryRecord:
        """Resolve the active schema version for a contract type at a point in time."""

        moment = at or _utc_now()
        candidates = [
            record
            for record in self._by_contract_type.get(contract_type, [])
            if record.status == "active"
            and record.effective_from <= moment
            and (record.deprecated_from is None or record.deprecated_from > moment)
        ]
        if not candidates:
            raise SchemaRegistryResolutionError(
                f"No active schema version found for contract '{contract_type}'."
            )
        return candidates[-1]

    def get_deprecated_versions(self, contract_type: str) -> list[SchemaRegistryRecord]:
        """Return deprecated versions for a contract type."""

        return [
            record
            for record in self._by_contract_type.get(contract_type, [])
            if record.status == "deprecated"
        ]
