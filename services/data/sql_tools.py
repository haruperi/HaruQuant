"""Read-only SQLite helpers for examples and internal tools."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class SQLMCPAccessError(ValueError):
    """Raised when a SQL query violates read-only access policy."""


@dataclass(frozen=True)
class SQLQueryResult:
    rows: list[dict[str, Any]]


class SQLReadOnlyTools:
    """Small read-only SQLite query helper with table allow-list enforcement."""

    def __init__(self, database_path: str | Path, allowed_tables: Iterable[str]):
        self.database_path = Path(database_path)
        self.allowed_tables = {table.lower() for table in allowed_tables}

    def execute_query(self, query: str) -> SQLQueryResult:
        normalized = query.strip()
        if not normalized.lower().startswith("select "):
            raise SQLMCPAccessError("Only SELECT queries are allowed.")

        referenced_tables = {
            match.group(1).lower()
            for match in re.finditer(r"\b(?:from|join)\s+([A-Za-z_][\w]*)", normalized, re.I)
        }
        denied_tables = referenced_tables - self.allowed_tables
        if denied_tables:
            denied = ", ".join(sorted(denied_tables))
            raise SQLMCPAccessError(f"Query references non-allowed tables: {denied}")

        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(normalized)
            return SQLQueryResult(rows=[dict(row) for row in cursor.fetchall()])
