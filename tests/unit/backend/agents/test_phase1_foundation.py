"""Unit tests for Phase 1 foundation fixes."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

# ──────────────────────────────────────────────────────────────
# Phase 1.1: MT5 Adapter Wiring
# ──────────────────────────────────────────────────────────────

from backend_retiring.mcp.mt5_mcp.server import (
    MT5MCPServer,
    create_legacy_mt5_mcp_server,
    create_mt5_mcp_server,
)
from backend_retiring.mcp.mt5_mcp.tools import MT5ReadOnlyTools, MT5MutatingTools, LegacyMT5GatewayAdapter


class FakeMT5Client:
    """Fake MT5 client returning predictable test data."""
    def account_info(self):
        return {"login": 12345, "balance": 10000.0, "currency": "USD"}

    def positions_get(self):
        return [{"ticket": 1, "symbol": "EURUSD", "volume": 0.1, "type": "BUY"}]

    def orders_get(self):
        return [{"ticket": 2, "symbol": "EURUSD", "price": 1.0850}]

    def symbol_info(self, symbol):
        return {"symbol": symbol, "spread": 10, "digits": 5}

    def get_ticks(self, symbol, count=10, as_dataframe=True):
        return [{"time": "2026-01-01", "bid": 1.0850, "ask": 1.0852}]

    def order_send(self, request):
        return {"retcode": 10009, "deal": 12345, "order": 67890}


def test_mt5_server_lists_all_tools() -> None:
    """Server should list both read-only and mutating tool specs."""
    server = create_mt5_mcp_server()
    tool_names = {t.name for t in server.list_tools()}
    assert "get_account_info" in tool_names
    assert "list_positions" in tool_names
    assert "place_order" in tool_names
    assert "full_close" in tool_names


def test_legacy_server_wires_tools() -> None:
    """Legacy server should wire read-only and mutating tools."""
    client = FakeMT5Client()
    server = create_legacy_mt5_mcp_server(client=client)
    assert server.read_only_tools is not None
    assert server.mutating_tools is not None
    assert server.started is False
    server.startup()
    assert server.started is True


def test_legacy_server_call_tool_routes() -> None:
    """call_tool should route to read-only or mutating tools."""
    client = FakeMT5Client()
    server = create_legacy_mt5_mcp_server(client=client)

    # Read-only tool
    result = server.call_tool("get_account_info", {})
    assert result["login"] == 12345
    assert result["balance"] == 10000.0

    # Another read-only tool
    positions = server.call_tool("list_positions", {})
    assert len(positions) == 1

    # Mutating tool (place_order takes a single 'request' dict)
    order_result = server.call_tool("place_order", {"request": {"symbol": "EURUSD", "action": "buy"}})
    assert order_result["retcode"] == 10009


def test_legacy_server_unknown_tool_raises() -> None:
    """Unknown tool name should raise KeyError."""
    client = FakeMT5Client()
    server = create_legacy_mt5_mcp_server(client=client)
    with pytest.raises(KeyError, match="nonexistent_tool"):
        server.call_tool("nonexistent_tool", {})


# ──────────────────────────────────────────────────────────────
# Phase 1.2: SQL Allowlist AST Parsing
# ──────────────────────────────────────────────────────────────

from backend_retiring.mcp.sql_mcp.tools import SQLReadOnlyTools, SQLMCPAccessError


def _make_sql_tools(db_path: str) -> SQLReadOnlyTools:
    return SQLReadOnlyTools(db_path, allowed_tables=("trades", "positions", "market_data", "strategies"))


def test_sql_ast_allows_simple_select() -> None:
    """Simple SELECT should be allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE trades (id INTEGER, symbol TEXT)")
        conn.execute("INSERT INTO trades VALUES (1, 'EURUSD')")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        result = tools.execute_query("SELECT * FROM trades")
        assert result.row_count == 1


def test_sql_ast_allows_join() -> None:
    """SELECT with JOIN should be allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE trades (id INTEGER, symbol TEXT)")
        conn.execute("CREATE TABLE positions (id INTEGER, symbol TEXT)")
        conn.execute("INSERT INTO trades VALUES (1, 'EURUSD')")
        conn.execute("INSERT INTO positions VALUES (1, 'EURUSD')")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        result = tools.execute_query(
            "SELECT t.symbol FROM trades t JOIN positions p ON t.id = p.id"
        )
        assert result.row_count == 1


def test_sql_ast_rejects_unauthorized_table() -> None:
    """Query referencing non-allowlisted table should be rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        with pytest.raises(SQLMCPAccessError, match="unauthorized tables"):
            tools.execute_query("SELECT * FROM users")


def test_sql_ast_rejects_non_select() -> None:
    """Non-SELECT queries should be rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE trades (id INTEGER)")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        with pytest.raises(SQLMCPAccessError, match="Only SELECT"):
            tools.execute_query("DELETE FROM trades")


def test_sql_ast_rejects_multi_statement() -> None:
    """Multi-statement queries should be rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE trades (id INTEGER)")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        with pytest.raises(SQLMCPAccessError, match="Multi-statement"):
            tools.execute_query("SELECT * FROM trades; DROP TABLE trades")


def test_sql_ast_prevents_subquery_bypass() -> None:
    """Subquery with unauthorized table should be rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        conn = __import__("sqlite3").connect(db)
        conn.execute("CREATE TABLE trades (id INTEGER)")
        conn.execute("CREATE TABLE users (id INTEGER)")
        conn.commit()
        conn.close()

        tools = _make_sql_tools(db)
        with pytest.raises(SQLMCPAccessError):
            tools.execute_query(
                "SELECT * FROM (SELECT * FROM users) AS trades"
            )


# ──────────────────────────────────────────────────────────────
# Phase 1.3: Pre-Execution Tool Validation
# ──────────────────────────────────────────────────────────────

from backend_retiring.agents.runtime.tool_validation import (
    ToolValidator,
    ToolValidationError,
    ToolParameterSchema,
    register_mcp_schemas,
)


def test_tool_validator_rejects_missing_required() -> None:
    """Missing required parameter should raise ToolValidationError."""
    v = ToolValidator()
    v.register_simple("place_order", required_fields=("symbol", "action"))

    with pytest.raises(ToolValidationError, match="requires parameter 'symbol'"):
        v.validate({"tool_name": "place_order", "parameters": {"action": "buy"}})


def test_tool_validator_accepts_valid() -> None:
    """Valid parameters should pass."""
    v = ToolValidator()
    v.register_simple("place_order", required_fields=("symbol", "action"))
    v.validate({"tool_name": "place_order", "parameters": {"symbol": "EURUSD", "action": "buy"}})


def test_tool_validator_unknown_tool_raises() -> None:
    """Unknown tool should raise ToolValidationError."""
    v = ToolValidator()
    with pytest.raises(ToolValidationError, match="Unknown tool"):
        v.validate({"tool_name": "nonexistent"})


def test_tool_validator_type_check() -> None:
    """Wrong parameter type should raise ToolValidationError."""
    v = ToolValidator()
    v.register_simple("get_ticks", required_fields=("symbol",), optional_fields={"count": "int"})

    with pytest.raises(ToolValidationError, match="expected type 'int'"):
        v.validate({"tool_name": "get_ticks", "parameters": {"symbol": "EURUSD", "count": "not_a_number"}})


def test_register_mcp_schemas() -> None:
    """MCP schemas should be pre-registered."""
    v = ToolValidator()
    register_mcp_schemas(v)
    # get_symbol_info requires "symbol"
    with pytest.raises(ToolValidationError, match="requires parameter 'symbol'"):
        v.validate({"tool_name": "get_symbol_info", "parameters": {}})


# ──────────────────────────────────────────────────────────────
# Phase 1.4: Tool Output Size Limits
# ──────────────────────────────────────────────────────────────

from backend_retiring.agents.runtime.middleware import _truncate_strings_in_dict


def test_truncate_strings_in_dict_short() -> None:
    """Short strings should pass through unchanged."""
    d = {"key": "short value", "nested": {"a": "b"}}
    result = _truncate_strings_in_dict(d, max_chars=1000)
    assert result["key"] == "short value"


def test_truncate_strings_in_dict_long() -> None:
    """Long strings should be truncated with marker."""
    long_str = "x" * 10000
    d = {"key": long_str}
    result = _truncate_strings_in_dict(d, max_chars=100)
    assert len(result["key"]) < 10000
    assert "...[tool output truncated]" in result["key"]


def test_truncate_strings_in_dict_nested() -> None:
    """Nested dicts and lists should be recursively truncated."""
    d = {
        "outer": {
            "inner": "y" * 10000,
        },
        "items": ["z" * 10000],
    }
    result = _truncate_strings_in_dict(d, max_chars=100)
    assert "...[tool output truncated]" in result["outer"]["inner"]
    assert "...[truncated]" in result["items"][0]


# ──────────────────────────────────────────────────────────────
# Phase 1.5: Schema Registry Persistence
# ──────────────────────────────────────────────────────────────

from contracts.schema_registry_persistence_service import (
    SchemaRegistryPersistence,
    create_persisted_registry,
)
from contracts.schema_registry import SchemaRegistryRecord
from datetime import datetime, timezone


def test_persistence_saves_and_loads() -> None:
    """Records should persist to SQLite and survive reload."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "schema_registry.db")
        persistence = SchemaRegistryPersistence(db)

        record = SchemaRegistryRecord(
            contract_type="TestContract",
            schema_version="v1",
            semantic_version="1.0.0",
            status="active",
            effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            deprecated_from=None,
            compatibility_policy="backward",
            payload_hash="abc123",
            json_schema_ref="test.json",
            pydantic_model_ref="TestContract",
            owning_domain_team="test",
            changelog_summary="Initial",
        )
        persistence.save(record)

        loaded = persistence.load_all()
        assert len(loaded) == 1
        assert loaded[0].contract_type == "TestContract"


def test_persistence_clear() -> None:
    """Clear should remove all persisted records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "schema_registry.db")
        persistence = SchemaRegistryPersistence(db)
        persistence.save(SchemaRegistryRecord(
            contract_type="A", schema_version="v1", semantic_version="1.0.0",
            status="active", effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            deprecated_from=None, compatibility_policy="backward",
            payload_hash="h1", json_schema_ref="r1", pydantic_model_ref="m1",
            owning_domain_team="t1", changelog_summary="log",
        ))
        count = persistence.clear()
        assert count >= 1
        assert len(persistence.load_all()) == 0


# ──────────────────────────────────────────────────────────────
# Phase 1.6: Model-Specific Cost Tracking
# ──────────────────────────────────────────────────────────────

from observability.cost_tracker import (
    CostTracker,
    get_model_pricing,
    calculate_cost,
    MODEL_PRICING,
)


def test_model_pricing_gemini_flash() -> None:
    """Gemini flash-lite should have correct pricing."""
    input_rate, output_rate = get_model_pricing("gemini-3.1-flash-lite-preview")
    assert input_rate == 0.075
    assert output_rate == 0.30


def test_model_pricing_gpt4o() -> None:
    """GPT-4o should have correct pricing."""
    input_rate, output_rate = get_model_pricing("gpt-4o")
    assert input_rate == 2.50
    assert output_rate == 10.00


def test_model_pricing_ollama_free() -> None:
    """Ollama local models should be free."""
    input_rate, output_rate = get_model_pricing("qwen2.5-coder:7b")
    assert input_rate == 0.0
    assert output_rate == 0.0


def test_model_pricing_unknown_logs_warning() -> None:
    """Unknown model should return $0.00 with warning."""
    input_rate, output_rate = get_model_pricing("totally_unknown_model_xyz")
    assert input_rate == 0.0
    assert output_rate == 0.0


def test_calculate_cost() -> None:
    """Cost calculation should be accurate."""
    # 1000 input + 500 output tokens for gemini-flash-lite
    cost = calculate_cost("gemini-3.1-flash-lite-preview", 1000, 500)
    expected = (1000 / 1_000_000 * 0.075) + (500 / 1_000_000 * 0.30)
    assert abs(cost - expected) < 1e-10


def test_cost_tracker_model_specific() -> None:
    """Cost tracker should use model-specific pricing."""
    tracker = CostTracker()
    tracker.record(trace_id="t1", model="gemini-3.1-flash-lite-preview", input_tokens=1000, output_tokens=500)
    tracker.record(trace_id="t2", model="gpt-4o", input_tokens=1000, output_tokens=500)

    # Gemini should be cheap
    cost_gemini = tracker.total_cost("t1")
    # GPT-4o should be expensive
    cost_gpt = tracker.total_cost("t2")

    assert cost_gpt > cost_gemini  # GPT-4o costs more than Gemini flash


def test_cost_breakdown_by_model() -> None:
    """Cost breakdown should group by model."""
    tracker = CostTracker()
    tracker.record(trace_id="t1", model="gemini-3.1-flash-lite-preview", input_tokens=1000, output_tokens=500)
    tracker.record(trace_id="t1", model="gpt-4o", input_tokens=1000, output_tokens=500)

    breakdown = tracker.cost_breakdown_by_model("t1")
    assert "gemini-3.1-flash-lite-preview" in breakdown
    assert "gpt-4o" in breakdown
    assert breakdown["gpt-4o"] > breakdown["gemini-3.1-flash-lite-preview"]
