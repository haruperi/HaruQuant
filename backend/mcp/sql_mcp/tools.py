"""Governed read-only SQL MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from backend.mcp.mt5_mcp.models import MCPToolSpec


class SQLMCPAccessError(ValueError):
    """Raised when a governed SQL MCP query violates policy."""


@dataclass(frozen=True)
class SQLQueryResult:
    """Stable result contract for governed SQL reads."""

    row_count: int
    columns: tuple[str, ...]
    rows: tuple[dict[str, object], ...]


class SQLReadOnlyTools:
    """Read-only governed SQL wrapper over the legacy SQLite access path."""

    def __init__(self, db_path: str | Path, *, allowed_tables: tuple[str, ...]) -> None:
        self._db_path = str(db_path)
        self._allowed_tables = tuple(sorted({table.lower() for table in allowed_tables}))

    def execute_query(self, query: str) -> SQLQueryResult:
        normalized = " ".join(query.strip().split())
        normalized_lower = normalized.lower()
        if not normalized_lower.startswith("select "):
            raise SQLMCPAccessError("only SELECT queries are allowed")
        if ";" in normalized_lower.rstrip(";"):
            raise SQLMCPAccessError("multi-statement queries are not allowed")

        allowed_reference = any(
            f" {table} " in f" {normalized_lower} "
            or f" {table}\n" in f" {normalized_lower}\n"
            or normalized_lower.endswith(f" {table}")
            for table in self._allowed_tables
        )
        if not allowed_reference:
            raise SQLMCPAccessError("query references tables outside the governed allowlist")

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(query).fetchall()
        finally:
            connection.close()

        normalized_rows = tuple(dict(row) for row in rows)
        columns = tuple(normalized_rows[0].keys()) if normalized_rows else ()
        return SQLQueryResult(
            row_count=len(normalized_rows),
            columns=columns,
            rows=normalized_rows,
        )


SQL_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("execute_query", "read", "Execute governed read-only SQL over an allowlisted table set."),
)


__all__ = [
    "SQLMCPAccessError",
    "SQLQueryResult",
    "SQLReadOnlyTools",
]
