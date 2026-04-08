"""SQLite-first migration framework baseline."""

from .runner import (
    MigrationRecord,
    apply_pending_migrations,
    discover_migrations,
    ensure_migration_table,
)

__all__ = [
    "MigrationRecord",
    "apply_pending_migrations",
    "discover_migrations",
    "ensure_migration_table",
]
