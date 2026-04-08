"""Database migration scaffolding for the agentic backend."""

from .migrations.runner import (
    MigrationRecord,
    apply_pending_migrations,
    discover_migrations,
    ensure_migration_table,
)
from .repositories import (
    ProposalRecord,
    ProposalRepository,
    WorkflowRecord,
    WorkflowRepository,
)

__all__ = [
    "MigrationRecord",
    "apply_pending_migrations",
    "discover_migrations",
    "ensure_migration_table",
    "ProposalRecord",
    "ProposalRepository",
    "WorkflowRecord",
    "WorkflowRepository",
]
