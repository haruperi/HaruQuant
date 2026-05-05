from __future__ import annotations

import sqlite3

import pytest

from backend_retiring.mcp.sql_mcp import SQLMCPAccessError, SQLMCPServer, SQLReadOnlyTools, create_sql_mcp_server


def test_sql_mcp_server_starts_with_expected_tool_spec() -> None:
    server = create_sql_mcp_server()

    assert isinstance(server, SQLMCPServer)
    assert server.name == "sql_mcp"
    assert server.started is False
    assert len(server.list_tools()) == 1


def test_sql_mcp_server_startup_marks_server_ready() -> None:
    server = create_sql_mcp_server()

    result = server.startup()

    assert result is server
    assert server.started is True


def test_sql_read_only_tools_execute_allowlisted_select_query(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE core_workflows (workflow_id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        connection.execute("INSERT INTO core_workflows (workflow_id, state) VALUES ('wf_001', 'CREATED')")
        connection.commit()
    finally:
        connection.close()

    tools = SQLReadOnlyTools(database_path, allowed_tables=("core_workflows",))

    result = tools.execute_query("SELECT workflow_id, state FROM core_workflows")

    assert result.row_count == 1
    assert result.columns == ("workflow_id", "state")
    assert result.rows[0]["workflow_id"] == "wf_001"


def test_sql_read_only_tools_reject_non_select_or_non_allowlisted_queries(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    sqlite3.connect(database_path).close()
    tools = SQLReadOnlyTools(database_path, allowed_tables=("core_workflows",))

    with pytest.raises(SQLMCPAccessError, match="only SELECT"):
        tools.execute_query("DELETE FROM core_workflows")

    with pytest.raises(SQLMCPAccessError, match="allowlist"):
        tools.execute_query("SELECT * FROM audit_trajectory_logs")
