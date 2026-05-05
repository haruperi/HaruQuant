"""Minimal SQLite-first migration runner for HaruQuant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sqlite3

from haruquant.utils import ErrorDescriptor, InfrastructureError


_INVALID_MIGRATION_NAME = ErrorDescriptor(
    code=4060,
    name="INVALID_MIGRATION_NAME",
    message="Migration filenames must follow '<version>_<name>.sql'.",
    domain="database",
)
_MIGRATION_CHECKSUM_MISMATCH = ErrorDescriptor(
    code=4061,
    name="MIGRATION_CHECKSUM_MISMATCH",
    message="Recorded migration does not match the on-disk migration file.",
    domain="database",
)
_MIGRATION_APPLY_FAILED = ErrorDescriptor(
    code=4062,
    name="MIGRATION_APPLY_FAILED",
    message="Failed to apply database migration.",
    domain="database",
)


@dataclass(frozen=True)
class MigrationRecord:
    """Metadata for a discovered migration file."""

    version: str
    name: str
    checksum: str
    path: Path


def _default_migrations_dir() -> Path:
    return Path(__file__).resolve().parent


def default_migrations_dir() -> Path:
    """Return the canonical SQL migration directory."""

    return _default_migrations_dir()


def _resolve_migrations_dir(migrations_dir: str | Path | None = None) -> Path:
    if migrations_dir is None:
        return _default_migrations_dir()

    return Path(migrations_dir)


def discover_migrations(migrations_dir: str | Path | None = None) -> list[MigrationRecord]:
    """Return migration files sorted by versioned filename."""

    root = _resolve_migrations_dir(migrations_dir)
    if not root.exists():
        return []

    migrations: list[MigrationRecord] = []
    for path in sorted(root.glob("*.sql")):
        version, _, remainder = path.stem.partition("_")
        if not version or not remainder:
            raise InfrastructureError(
                _INVALID_MIGRATION_NAME,
                f"Migration filename is invalid: {path}.",
            )

        migrations.append(
            MigrationRecord(
                version=version,
                name=remainder.replace("_", "-"),
                checksum=sha256(path.read_bytes()).hexdigest(),
                path=path,
            )
        )

    return migrations


def ensure_migration_table(connection: sqlite3.Connection) -> None:
    """Ensure the migration history table exists."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _load_applied_versions(connection: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    rows = connection.execute(
        "SELECT version, checksum, name FROM _schema_migrations"
    ).fetchall()
    return {str(version): (str(checksum), str(name)) for version, checksum, name in rows}


def apply_pending_migrations(
    db_path: str | Path,
    migrations_dir: str | Path | None = None,
) -> list[MigrationRecord]:
    """Apply all pending SQL migrations to the target SQLite database."""

    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    discovered = discover_migrations(migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        ensure_migration_table(connection)
        applied_versions = _load_applied_versions(connection)
        applied_now: list[MigrationRecord] = []

        for migration in discovered:
            existing = applied_versions.get(migration.version)
            if existing is not None:
                existing_checksum, existing_name = existing
                if existing_checksum != migration.checksum or existing_name != migration.name:
                    raise InfrastructureError(
                        _MIGRATION_CHECKSUM_MISMATCH,
                        "Recorded migration does not match the on-disk migration file: "
                        f"version={migration.version}, recorded={existing_name}, current={migration.name}.",
                    )
                continue

            script = migration.path.read_text(encoding="utf-8")
            applied_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            try:
                with connection:
                    connection.executescript(script)
                    connection.execute(
                        """
                        INSERT INTO _schema_migrations (version, name, checksum, applied_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            migration.version,
                            migration.name,
                            migration.checksum,
                            applied_at,
                        ),
                    )
            except sqlite3.Error as exc:
                raise InfrastructureError(
                    _MIGRATION_APPLY_FAILED,
                    f"Failed to apply database migration {migration.version} at {migration.path}.",
                ) from exc

            applied_now.append(migration)

        return applied_now
    finally:
        connection.close()
