"""SQLite persistence layer for schema registry records."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Iterable

from .schema_registry import SchemaRegistryRecord
from .schema_registry_persistence import record_to_row, row_to_record
from .schema_registry_seeds import load_initial_schema_registry_seeds
from datetime import datetime


class SchemaRegistryPersistenceError(RuntimeError):
    """Raised when schema registry persistence operation fails."""


class SchemaRegistryPersistence:
    """SQLite-backed persistence for schema registry records."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create the schema_registry table if it doesn't exist."""
        os.makedirs(os.path.dirname(self._db_path) if os.path.dirname(self._db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_type TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    semantic_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    effective_from TEXT NOT NULL,
                    deprecated_from TEXT,
                    compatibility_policy TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    json_schema_ref TEXT NOT NULL,
                    pydantic_model_ref TEXT NOT NULL,
                    owning_domain_team TEXT NOT NULL,
                    changelog_summary TEXT NOT NULL,
                    UNIQUE(contract_type, schema_version)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save(self, record: SchemaRegistryRecord) -> None:
        """Upsert a schema registry record."""
        row = record_to_row(record)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO schema_registry
                   (contract_type, schema_version, semantic_version, status,
                    effective_from, deprecated_from, compatibility_policy,
                    payload_hash, json_schema_ref, pydantic_model_ref,
                    owning_domain_team, changelog_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row.contract_type,
                    row.schema_version,
                    row.semantic_version,
                    row.status,
                    row.effective_from.isoformat(),
                    row.deprecated_from.isoformat() if row.deprecated_from else None,
                    row.compatibility_policy,
                    row.payload_hash,
                    row.json_schema_ref,
                    row.pydantic_model_ref,
                    row.owning_domain_team,
                    row.changelog_summary,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load_all(self) -> list[SchemaRegistryRecord]:
        """Load all persisted schema registry records."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM schema_registry").fetchall()
        finally:
            conn.close()
        return [row_to_record({k: v for k, v in dict(row).items() if k != "id"}) for row in rows]

    def load_by_type(self, contract_type: str) -> list[SchemaRegistryRecord]:
        """Load records for a specific contract type."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM schema_registry WHERE contract_type = ?",
                (contract_type,),
            ).fetchall()
        finally:
            conn.close()
        return [row_to_record(dict(row)) for row in rows]

    def clear(self) -> int:
        """Delete all persisted records. Returns count deleted."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("DELETE FROM schema_registry")
            count = cursor.rowcount
            conn.commit()
            return count
        finally:
            conn.close()


def create_persisted_registry(db_path: str) -> "SchemaRegistryService":
    """Create a SchemaRegistryService backed by SQLite persistence.

    Loads persisted records on startup, merging with seed records.
    Persists changes back to SQLite on save.
    """
    from .schema_registry_service import SchemaRegistryService

    persistence = SchemaRegistryPersistence(db_path)

    # Load persisted records
    persisted = persistence.load_all()

    # Load seed records
    seeds = list(load_initial_schema_registry_seeds())

    # Merge: seeds + persisted (persisted takes precedence for same version)
    seed_map = {f"{s.contract_type}:{s.schema_version}": s for s in seeds}
    for p in persisted:
        seed_map[f"{p.contract_type}:{p.schema_version}"] = p

    all_records = list(seed_map.values())
    return SchemaRegistryService(all_records)
