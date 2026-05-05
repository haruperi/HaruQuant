"""Create new strategy versions with legacy ``apps`` imports migrated.

The script preserves historical saved files. It writes a new strategy version
for each active legacy strategy, validates the migrated version can be loaded,
updates the active version, and refreshes governance hashes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data.database.sqlite.database_operations import DatabaseManager
from services.strategy import (
    StrategyCatalogService,
    StrategyCatalogUpdateRequest,
    governance_strategy_id,
    storage,
)


REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^from\s+apps\.strategy\.base\s+import\s+(.+)$", re.MULTILINE),
        r"from services.strategy.base import \1",
    ),
    (
        re.compile(r"^from\s+apps\.indicator\s+import\s+(.+)$", re.MULTILINE),
        r"from services.indicator import \1",
    ),
    (
        re.compile(r"^from\s+apps\.utils\.logger\s+import\s+logger\s*$", re.MULTILINE),
        "from services.utils.logger import logger",
    ),
    (
        re.compile(r"^from\s+apps\.trading\s+import\s+(.+)$", re.MULTILINE),
        r"from services.strategy.compat_types import \1",
    ),
    (
        re.compile(r"^from\s+apps\.trade\s+import\s+(.+)$", re.MULTILINE),
        r"from services.strategy.compat_types import \1",
    ),
)


def migrate_strategy_imports(code: str) -> str:
    migrated = code
    migrated = re.sub(
        r"^from\s+apps\.strategy\s+import\s+Strategy\s*$",
        "from services.strategy import BaseStrategy as Strategy",
        migrated,
        flags=re.MULTILINE,
    )
    migrated = re.sub(
        r"^from\s+apps\.strategy\s+import\s+BaseStrategy\s*$",
        "from services.strategy import BaseStrategy",
        migrated,
        flags=re.MULTILINE,
    )
    migrated = re.sub(
        r"^from\s+apps\.strategy\s+import\s+BaseStrategy\s+as\s+(.+)$",
        r"from services.strategy import BaseStrategy as \1",
        migrated,
        flags=re.MULTILINE,
    )
    migrated = re.sub(
        r"^from\s+apps\.strategy\s+import\s+Strategy\s+as\s+(.+)$",
        r"from services.strategy import BaseStrategy as \1",
        migrated,
        flags=re.MULTILINE,
    )
    for pattern, replacement in REPLACEMENTS:
        migrated = pattern.sub(replacement, migrated)
    return migrated


def has_legacy_apps_import(code: str) -> bool:
    return bool(re.search(r"^\s*(from|import)\s+apps(\.|\s|$)", code, flags=re.MULTILINE))


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _load_active_strategy_rows(db_path: Path) -> list[sqlite3.Row]:
    with _connect(db_path) as connection:
        return connection.execute(
            """
            SELECT
                s.id AS strategy_id,
                s.user_id,
                s.name,
                s.category,
                s.strategy_family,
                s.active_version_id,
                u.username,
                sv.version,
                sv.file_path,
                sv.parameters
            FROM strategies s
            JOIN users u ON u.id = s.user_id
            JOIN strategy_versions sv ON sv.id = s.active_version_id
            ORDER BY s.id
            """
        ).fetchall()


def _parameters(row: sqlite3.Row) -> Dict[str, Any]:
    raw = row["parameters"]
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _read_code(row: sqlite3.Row) -> str:
    file_path = row["file_path"]
    if file_path and Path(str(file_path)).exists():
        return Path(str(file_path)).read_text(encoding="utf-8")
    return storage.load_strategy_code(
        user_id=int(row["user_id"]),
        strategy_id=int(row["strategy_id"]),
        version=str(row["version"]),
        username=str(row["username"]),
        strategy_name=str(row["name"]),
    )


def _validate_migrated_code(
    *,
    code: str,
    strategy_id: int,
    version: str,
) -> None:
    compile(code, f"<strategy:{strategy_id}:{version}>", "exec")
    validation_root = PROJECT_ROOT / "build" / "tmp" / "strategy_import_migration"
    validation_dir = validation_root / f"strategy_{strategy_id}_{version.replace('.', '_')}"
    if validation_dir.exists():
        shutil.rmtree(validation_dir)
    validation_dir.mkdir(parents=True, exist_ok=True)
    try:
        tmp_storage = type(storage)(base_dir=str(validation_dir))
        tmp_storage.save_strategy(
            user_id=1,
            strategy_id=strategy_id,
            version=version,
            code=code,
            username="validation",
            strategy_name=f"strategy-{strategy_id}",
        )
        tmp_storage.load_strategy_class(
            user_id=1,
            strategy_id=strategy_id,
            version=version,
            username="validation",
            strategy_name=f"strategy-{strategy_id}",
        )
    finally:
        shutil.rmtree(validation_dir, ignore_errors=True)


def migrate_active_strategies(
    *,
    db_path: Path,
    strategy_ids: Optional[set[int]],
    apply: bool,
) -> Dict[str, Any]:
    service = StrategyCatalogService(db_manager=DatabaseManager())
    rows = _load_active_strategy_rows(db_path)
    results: Dict[str, Any] = {
        "checked": 0,
        "migrated": [],
        "skipped": [],
        "failed": [],
    }

    for row in rows:
        strategy_id = int(row["strategy_id"])
        if strategy_ids and strategy_id not in strategy_ids:
            continue
        results["checked"] += 1
        try:
            original = _read_code(row)
        except Exception as exc:
            results["failed"].append(
                {"strategy_id": strategy_id, "name": row["name"], "reason": str(exc)}
            )
            continue

        migrated = migrate_strategy_imports(original)
        if migrated == original or not has_legacy_apps_import(original):
            results["skipped"].append(
                {
                    "strategy_id": strategy_id,
                    "name": row["name"],
                    "reason": "no active legacy apps imports",
                }
            )
            continue
        if has_legacy_apps_import(migrated):
            results["failed"].append(
                {
                    "strategy_id": strategy_id,
                    "name": row["name"],
                    "reason": "unmapped apps import remains after rewrite",
                }
            )
            continue

        try:
            _validate_migrated_code(
                code=migrated,
                strategy_id=strategy_id,
                version=str(row["version"]),
            )
        except Exception as exc:
            results["failed"].append(
                {
                    "strategy_id": strategy_id,
                    "name": row["name"],
                    "reason": f"validation failed: {exc}",
                }
            )
            continue

        if apply:
            new_version = service.update_strategy(
                strategy_id,
                StrategyCatalogUpdateRequest(
                    code=migrated,
                    parameters=_parameters(row),
                    changelog="Migrated legacy apps imports to backend.services paths",
                ),
                user_id=int(row["user_id"]),
            ).get("active_version")
        else:
            new_version = None

        results["migrated"].append(
            {
                "strategy_id": strategy_id,
                "name": row["name"],
                "from_version": row["version"],
                "to_version": new_version or "(dry-run)",
                "governance_strategy_id": governance_strategy_id(
                    int(row["user_id"]),
                    strategy_id,
                ),
            }
        )

    return results


def parse_strategy_ids(values: Optional[Iterable[str]]) -> Optional[set[int]]:
    if not values:
        return None
    strategy_ids: set[int] = set()
    for value in values:
        for token in value.split(","):
            token = token.strip()
            if token:
                strategy_ids.add(int(token))
    return strategy_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=PROJECT_ROOT / "backend" / "data" / "database" / "haruquant.db",
    )
    parser.add_argument("--strategy-id", action="append", help="Strategy ID or comma-separated IDs")
    parser.add_argument("--apply", action="store_true", help="Write new versions and switch active versions")
    args = parser.parse_args()

    results = migrate_active_strategies(
        db_path=args.db_path,
        strategy_ids=parse_strategy_ids(args.strategy_id),
        apply=bool(args.apply),
    )
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
