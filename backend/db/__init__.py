"""Database migration scaffolding for the agentic backend."""

from .migrations.runner import (
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
