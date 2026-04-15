"""Backfill legacy strategy catalog rows into the agentic governance registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any
from hashlib import sha256

from backend.data.database.migrations.runner import apply_pending_migrations, default_migrations_dir
from backend.data.database.repositories.governance_repository import GovernanceRepository


def canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def code_hash(code: str) -> str:
    return sha256((code or "").encode("utf-8")).hexdigest()


def governance_strategy_id(user_id: int, strategy_id: int) -> str:
    return f"strategy:{user_id}:{strategy_id}"


def _ensure_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(strategies)").fetchall()
    }
    additions = {
        "governance_strategy_id": "TEXT",
        "artifact_root": "TEXT",
        "strategy_family": "TEXT",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE strategies ADD COLUMN {name} {definition}")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_strategies_governance_strategy_id "
        "ON strategies (governance_strategy_id)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_strategies_user_family_updated "
        "ON strategies (user_id, strategy_family, updated_at DESC)"
    )


def _load_parameters(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _artifact_root(file_path: str | None) -> str | None:
    if not file_path:
        return None
    path = Path(file_path)
    if path.name == "strategy.py":
        return str(path.parent.parent)
    return str(path.parent)


def _resolve_strategy_file(file_path: str | None) -> Path | None:
    if not file_path:
        return None

    normalized = str(file_path).replace("\\", "/")
    marker = "data/strategies/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        candidate = Path("backend") / "data" / "strategies" / Path(suffix)
        if candidate.exists():
            return candidate

    original = Path(file_path)
    if original.exists():
        return original
    return None


def migrate(db_path: str, *, apply: bool = False) -> dict[str, Any]:
    if apply:
        apply_pending_migrations(db_path, default_migrations_dir())
    governance = GovernanceRepository(db_path)
    report: dict[str, Any] = {
        "db_path": db_path,
        "apply": apply,
        "registered": [],
        "missing_files": [],
        "skipped": [],
    }

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        if apply:
            _ensure_columns(connection)
        strategies = connection.execute("SELECT * FROM strategies ORDER BY id").fetchall()
        versions_by_strategy: dict[int, list[dict[str, Any]]] = {}
        for version_row in connection.execute(
            "SELECT * FROM strategy_versions ORDER BY created_at DESC, id DESC"
        ).fetchall():
            version = dict(version_row)
            versions_by_strategy.setdefault(int(version["strategy_id"]), []).append(version)
        if apply:
            connection.commit()
    finally:
        connection.close()

    for row in strategies:
        strategy = dict(row)
        strategy_id = int(strategy["id"])
        user_id = int(strategy["user_id"])
        versions = versions_by_strategy.get(strategy_id, [])
        active_version_id = strategy.get("active_version_id")
        version = None
        if active_version_id:
            version = next(
                (item for item in versions if int(item["id"]) == int(active_version_id)),
                None,
            )
        if version is None and versions:
            version = versions[0]
        if version is None:
            report["skipped"].append(
                {"strategy_id": strategy_id, "reason": "no_strategy_versions"}
            )
            continue

        file_path = str(version.get("file_path") or "")
        resolved_file = _resolve_strategy_file(file_path)
        if resolved_file is None:
            missing = {
                "strategy_id": strategy_id,
                "version_id": version.get("id"),
                "file_path": file_path,
            }
            report["missing_files"].append(missing)
            report["skipped"].append({**missing, "reason": "missing_strategy_file"})
            continue
        else:
            source_hash = code_hash(resolved_file.read_text(encoding="utf-8"))

        family = str(strategy.get("strategy_family") or strategy.get("category") or "custom")
        gov_id = governance_strategy_id(user_id, strategy_id)
        parameter_hash = canonical_json_hash(_load_parameters(version.get("parameters")))
        artifact_root = _artifact_root(str(resolved_file) if resolved_file else file_path)

        if apply:
            connection = sqlite3.connect(db_path)
            try:
                with connection:
                    connection.execute(
                        """
                        UPDATE strategies
                        SET governance_strategy_id = ?,
                            artifact_root = ?,
                            strategy_family = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (gov_id, artifact_root, family, strategy_id),
                    )
            finally:
                connection.close()
            governance.upsert_strategy(
                strategy_id=gov_id,
                strategy_name=str(strategy["name"]),
                strategy_family=family,
                current_lifecycle_state="RESEARCH",
                code_hash=source_hash,
                parameter_hash=parameter_hash,
                owner_id=str(user_id),
            )

        report["registered"].append(
            {
                "strategy_id": strategy_id,
                "governance_strategy_id": gov_id,
                "strategy_name": strategy["name"],
                "strategy_family": family,
                "code_hash": source_hash,
                "parameter_hash": parameter_hash,
                "artifact_root": artifact_root,
            }
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        default="backend/data/database/haruquant.db",
        help="Path to the SQLite database.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag the script only reports planned changes.",
    )
    args = parser.parse_args()
    print(json.dumps(migrate(args.db_path, apply=args.apply), indent=2))


if __name__ == "__main__":
    main()
