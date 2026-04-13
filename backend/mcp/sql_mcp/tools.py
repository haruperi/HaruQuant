"""Governed read-only SQL MCP tools with AST-based table validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

import sqlparse
from sqlparse.sql import Identifier, Parenthesis
from sqlparse.tokens import Name

from backend.mcp.mt5_mcp.models import MCPToolSpec


class SQLMCPAccessError(ValueError):
    """Raised when a governed SQL MCP query violates policy."""


@dataclass(frozen=True)
class SQLQueryResult:
    """Stable result contract for governed SQL reads."""

    row_count: int
    columns: tuple[str, ...]
    rows: tuple[dict[str, object], ...]


def _extract_tables_from_sql(query: str) -> set[str]:
    """Extract table names from a SQL query using regex + structure.

    Uses regex to find table names after FROM/JOIN/INTO/UPDATE keywords,
    then validates structure with sqlparse.
    """
    tables: set[str] = set()

    # Pattern to find table references after FROM/JOIN keywords
    # Matches: FROM table_name, JOIN table_name, INTO table_name, UPDATE table_name
    # Handles aliases: FROM table_name alias, JOIN table_name AS alias
    # Handles subqueries: FROM (SELECT ...) but also catches inner FROM
    table_pattern = re.compile(
        r'\b(?:FROM|JOIN|INTO|UPDATE)\s+'
        r'(?:\(\s*SELECT\b.*?\)\s*(?:AS\s+)?)?'  # optional subquery
        r'([a-zA-Z_][a-zA-Z0-9_]*)',             # table name
        re.IGNORECASE | re.DOTALL,
    )

    for match in table_pattern.finditer(query):
        table_name = match.group(1).lower()
        if table_name and table_name not in _SQL_KEYWORDS:
            tables.add(table_name)

    # Also catch table names inside subqueries (recursive)
    subquery_pattern = re.compile(r'\(\s*(SELECT\s+.*?)\)', re.IGNORECASE | re.DOTALL)
    for sub_match in subquery_pattern.finditer(query):
        sub_tables = _extract_tables_from_sql(sub_match.group(1))
        tables.update(sub_tables)

    return tables


# SQL keywords that should never be treated as table names
_SQL_KEYWORDS = frozenset({
    "select", "from", "where", "and", "or", "not", "in", "like", "between",
    "is", "null", "true", "false", "as", "on", "join", "inner", "left",
    "right", "outer", "cross", "natural", "using", "group", "by", "order",
    "asc", "desc", "limit", "offset", "having", "distinct", "all", "any",
    "exists", "case", "when", "then", "else", "end", "union", "intersect",
    "except", "insert", "into", "values", "update", "set", "delete", "drop",
    "create", "alter", "table", "index", "view", "trigger", "function",
    "return", "returns", "begin", "commit", "rollback", "transaction",
    "count", "sum", "avg", "min", "max", "cast", "coalesce", "nullif",
    "primary", "key", "foreign", "references", "constraint", "default",
    "check", "unique", "database", "schema", "with", "rowid",
})


class SQLReadOnlyTools:
    """Read-only governed SQL wrapper with table allowlist validation."""

    def __init__(self, db_path: str | Path, *, allowed_tables: tuple[str, ...]) -> None:
        self._db_path = str(db_path)
        self._allowed_tables = frozenset(table.lower() for table in allowed_tables)

    def execute_query(self, query: str) -> SQLQueryResult:
        """Execute a read-only SQL query with table allowlist validation."""
        self._validate_query(query)

        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.execute(query)
            rows = cursor.fetchall()
        finally:
            connection.close()

        normalized_rows = tuple(dict(row) for row in rows)
        columns = tuple(normalized_rows[0].keys()) if normalized_rows else ()
        return SQLQueryResult(
            row_count=len(normalized_rows),
            columns=columns,
            rows=normalized_rows,
        )

    def _validate_query(self, query: str) -> None:
        """Validate query — rejects unauthorized tables and dangerous operations."""
        # Check 1: Must start with SELECT
        stripped = query.strip()
        if not re.match(r"^\s*SELECT\b", stripped, re.IGNORECASE):
            raise SQLMCPAccessError("Only SELECT queries are allowed")

        # Check 2: No multi-statement
        if ";" in stripped.rstrip("; "):
            raise SQLMCPAccessError("Multi-statement queries are not allowed")

        # Check 3: Parse to verify it's valid SQL and check type
        parsed = sqlparse.parse(stripped)
        if len(parsed) > 1:
            raise SQLMCPAccessError("Multi-statement queries are not allowed")

        stmt = parsed[0]
        stmt_type = stmt.get_type()
        if stmt_type and stmt_type.upper() != "SELECT":
            raise SQLMCPAccessError("Only SELECT queries are allowed")

        # Check 4: Extract all table references
        tables = _extract_tables_from_sql(stripped)

        # Check 5: All referenced tables must be in allowlist
        unauthorized = tables - self._allowed_tables
        if unauthorized:
            raise SQLMCPAccessError(
                f"Query references unauthorized tables: {', '.join(sorted(unauthorized))}. "
                f"Allowed tables: {', '.join(sorted(self._allowed_tables))}"
            )


SQL_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("execute_query", "read", "Execute governed read-only SQL over an allowlisted table set."),
)


__all__ = [
    "SQLMCPAccessError",
    "SQLQueryResult",
    "SQLReadOnlyTools",
    "_extract_tables_from_sql",
]
