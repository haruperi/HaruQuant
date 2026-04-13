"""Tool-Using Agents — Native Function Calling Examples.

Demonstrates the native tool calling system that replaced regex-based
ReAct parsing. Agents now use structured ToolCall/ToolResult contracts
with pre-execution validation, error handling, and audit logging.

Covers:
  - ToolCall and ToolResult data models
  - ToolExecutor with batch dispatch and error recovery
  - Pre-execution parameter validation (ToolValidator)
  - Output size limiting and truncation
  - Integration with MCP tools (SQL, MT5, retrieval)
  - ReAct agent migration path

Usage:
    python backend/scripts/examples/agentic_ai/03_tool_using_agents.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Core tool calling ─────────────────────────────────────────────────
from backend.agents.runtime import (
    ToolCall,
    ToolResult,
    ToolExecutor,
    _estimate_tokens,
)
from backend.agents.runtime.tool_validation import (
    ToolValidator,
    ToolValidationError,
    register_mcp_schemas,
)

# ── MCP tools ─────────────────────────────────────────────────────────
from backend.mcp.sql_mcp.tools import SQLReadOnlyTools, SQLMCPAccessError

# ── RAG retrieval (used as a tool) ────────────────────────────────────
from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.ingestion import DocumentIngester
from backend.retrieval.service import RetrievalService

# ── Cost tracking ─────────────────────────────────────────────────────
from backend.observability.cost_tracker import CostTracker


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, dict):
        print(f"  {label:<30s}")
        for k, v in value.items():
            print(f"    {k:<20s} {v}")
    else:
        print(f"  {label:<30s} {value}")


def print_result(r: ToolResult) -> None:
    status = "✅ OK" if not r.is_error else "❌ ERROR"
    print_kv(f"{r.tool_call_id} → {r.tool_name}", f"{status}")
    if not r.is_error:
        try:
            data = json.loads(r.output)
            print_kv("  output", data)
        except json.JSONDecodeError:
            print_kv("  output", r.output[:200])
    else:
        print_kv("  error", r.error)


# ────────────────────────────────────────────────────────────────────────
# Tool definitions for the examples
# ────────────────────────────────────────────────────────────────────────

def get_market_price(symbol: str) -> dict[str, Any]:
    """Get current market price for a symbol."""
    prices = {
        "EURUSD": {"bid": 1.0850, "ask": 1.0852, "spread": 2},
        "GBPUSD": {"bid": 1.2650, "ask": 1.2653, "spread": 3},
        "USDJPY": {"bid": 151.50, "ask": 151.52, "spread": 2},
    }
    return prices.get(symbol, {"error": f"Unknown symbol: {symbol}"})


def calculate_position_size(
    account_balance: float,
    risk_pct: float = 0.02,
    stop_loss_pips: float = 50.0,
    pip_value: float = 10.0,
) -> dict[str, Any]:
    """Calculate safe position size based on risk parameters."""
    risk_amount = account_balance * risk_pct
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    return {
        "risk_amount": round(risk_amount, 2),
        "lot_size": round(lot_size, 2),
        "risk_pct": risk_pct * 100,
        "stop_loss_pips": stop_loss_pips,
    }


def assess_correlation(symbol_a: str, symbol_b: str) -> dict[str, Any]:
    """Assess correlation between two symbols."""
    # Simulated correlation matrix
    correlations = {
        ("EURUSD", "GBPUSD"): 0.85,
        ("EURUSD", "USDJPY"): -0.60,
        ("GBPUSD", "USDJPY"): -0.55,
        ("EURUSD", "EURJPY"): 0.90,
    }
    key = (symbol_a, symbol_b)
    corr = correlations.get(key, correlations.get((symbol_b, symbol_a), 0.0))
    return {
        "symbol_a": symbol_a,
        "symbol_b": symbol_b,
        "correlation": corr,
        "risk_note": "High correlation increases portfolio risk" if abs(corr) > 0.8 else "Moderate correlation",
    }


# ────────────────────────────────────────────────────────────────────────
# Examples
# ────────────────────────────────────────────────────────────────────────

def example_01_tool_call_models() -> None:
    """ToolCall and ToolResult: structured contracts for tool invocation."""
    print_header("Example 01: ToolCall & ToolResult Models")

    # Creating a tool call
    call = ToolCall(
        tool_call_id="call_001",
        tool_name="get_market_price",
        parameters={"symbol": "EURUSD"},
        metadata={"source": "agent_reasoning", "step": 1},
    )
    print_kv("ToolCall created:", {
        "id": call.tool_call_id,
        "tool": call.tool_name,
        "params": call.parameters,
        "metadata": call.metadata,
    })

    # Simulating a result
    result = ToolResult(
        tool_call_id=call.tool_call_id,
        tool_name=call.tool_name,
        output=json.dumps({"bid": 1.0850, "ask": 1.0852}),
        token_count=8,
        latency_ms=15,
    )
    print_kv("ToolResult:", {
        "id": result.tool_call_id,
        "output": result.output,
        "tokens": result.token_count,
        "latency_ms": result.latency_ms,
    })

    # Error result
    error_result = ToolResult(
        tool_call_id="call_002",
        tool_name="get_market_price",
        output="Error: Unknown symbol: XYZUSD",
        error="Unknown symbol: XYZUSD",
        is_error=True,
        latency_ms=2,
    )
    print_kv("Error result:", {
        "id": error_result.tool_call_id,
        "is_error": error_result.is_error,
        "error": error_result.error,
    })


def example_02_tool_executor() -> None:
    """ToolExecutor: batch dispatch with error handling."""
    print_header("Example 02: Tool Executor — Batch Dispatch")

    executor = ToolExecutor(tools={
        "get_market_price": get_market_price,
        "calculate_position_size": calculate_position_size,
        "assess_correlation": assess_correlation,
    })

    # Batch: mix of valid, invalid, and unknown tool calls
    calls = [
        ToolCall(tool_call_id="c1", tool_name="get_market_price", parameters={"symbol": "EURUSD"}),
        ToolCall(tool_call_id="c2", tool_name="calculate_position_size", parameters={
            "account_balance": 10000, "risk_pct": 0.02, "stop_loss_pips": 50,
        }),
        ToolCall(tool_call_id="c3", tool_name="assess_correlation", parameters={
            "symbol_a": "EURUSD", "symbol_b": "GBPUSD",
        }),
        ToolCall(tool_call_id="c4", tool_name="unknown_tool", parameters={}),
        ToolCall(tool_call_id="c5", tool_name="get_market_price", parameters={"symbol": "XYZUSD"}),
    ]

    results = executor.execute(calls)
    print_kv("Calls submitted:", len(calls))
    print_kv("Results returned:", len(results))
    print_kv("Successful:", sum(1 for r in results if not r.is_error))
    print_kv("Failed:", sum(1 for r in results if r.is_error))

    print()
    for r in results:
        print_result(r)
        print()


def example_03_pre_execution_validation() -> None:
    """ToolValidator: catches bad parameters BEFORE execution."""
    print_header("Example 03: Pre-Execution Validation")

    validator = ToolValidator()
    register_mcp_schemas(validator)

    # Register our custom tools
    validator.register_simple("get_market_price", required_fields=("symbol",))
    validator.register_simple("calculate_position_size", required_fields=("account_balance",),
                              optional_fields={"risk_pct": "float", "stop_loss_pips": "float"})

    # Valid calls
    valid_calls = [
        {"tool_name": "get_market_price", "parameters": {"symbol": "EURUSD"}},
        {"tool_name": "calculate_position_size", "parameters": {"account_balance": 10000}},
    ]

    for call in valid_calls:
        try:
            validator.validate(call)
            print_kv(f"✅ Valid: {call['tool_name']}", call["parameters"])
        except ToolValidationError as exc:
            print_kv(f"❌ Invalid: {call['tool_name']}", str(exc))

    # Invalid calls
    invalid_calls = [
        {"tool_name": "get_market_price", "parameters": {}},  # missing 'symbol'
        {"tool_name": "calculate_position_size", "parameters": {"account_balance": "not_a_number"}},  # wrong type
        {"tool_name": "nonexistent_tool", "parameters": {}},  # unknown tool
    ]

    print()
    for call in invalid_calls:
        try:
            validator.validate(call)
            print_kv(f"✅ Valid: {call['tool_name']}", call["parameters"])
        except ToolValidationError as exc:
            print_kv(f"❌ Invalid: {call['tool_name']}", str(exc))


def example_04_tool_output_limits() -> None:
    """Tool output size limits prevent context overflow."""
    print_header("Example 04: Tool Output Size Limits")

    def large_data_generator(size: int = 10000) -> dict[str, Any]:
        """Generate a large payload that exceeds token budget."""
        return {
            "data": "x" * size,
            "metadata": {"items": size, "generated": True},
        }

    executor = ToolExecutor(
        tools={"generate_large": large_data_generator},
        max_output_tokens=1000,  # ~4000 chars
    )

    # Normal call
    results = executor.execute([
        ToolCall(tool_call_id="c1", tool_name="generate_large", parameters={"size": 100}),
    ])
    print_kv("Small output (100 chars):", f"length={len(results[0].output)}, truncated={'[truncated]' in results[0].output}")

    # Oversized call
    results = executor.execute([
        ToolCall(tool_call_id="c2", tool_name="generate_large", parameters={"size": 100000}),
    ])
    print_kv("Large output (100K chars):", f"length={len(results[0].output)}, truncated={'[truncated]' in results[0].output}")
    print_kv("Truncated preview:", results[0].output[:80] + "...")


def example_05_sql_tool_with_validation() -> None:
    """SQL MCP tool: governed read-only access with AST-based validation."""
    print_header("Example 05: SQL Tool with AST Validation")

    with tempfile.TemporaryDirectory() as tmpdir:
        import sqlite3
        db = os.path.join(tmpdir, "trading.db")
        conn = sqlite3.connect(db)
        conn.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                created_at TEXT
            )
        """)
        conn.execute("INSERT INTO trades VALUES (1, 'EURUSD', 'BUY', 1.0850, 1.0920, 700.00, '2026-04-13')")
        conn.execute("INSERT INTO trades VALUES (2, 'GBPUSD', 'SELL', 1.2700, 1.2650, 500.00, '2026-04-13')")
        conn.execute("INSERT INTO trades VALUES (3, 'EURUSD', 'BUY', 1.0800, 1.0750, -500.00, '2026-04-12')")
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT, api_key TEXT)")
        conn.execute("INSERT INTO users VALUES (1, 'admin', 'secret_key_123')")
        conn.commit()
        conn.close()

        sql_tools = SQLReadOnlyTools(db, allowed_tables=("trades",))

        # Allowed: query trades
        print("  ┌─ ALLOWED QUERIES ───────────────────────────────────┐")
        result = sql_tools.execute_query("SELECT symbol, direction, pnl FROM trades WHERE pnl > 0")
        print_kv(f"  Profitable trades:", f"{result.row_count} rows")
        for row in result.rows:
            print_kv(f"    {row['symbol']} {row['direction']}", f"PnL=${row['pnl']:.2f}")

        # Allowed: aggregate
        result = sql_tools.execute_query(
            "SELECT symbol, COUNT(*) as count, SUM(pnl) as total_pnl FROM trades GROUP BY symbol"
        )
        print_kv(f"  Aggregated by symbol:", f"{result.row_count} groups")
        for row in result.rows:
            print_kv(f"    {row['symbol']}", f"count={row['count']}, total_pnl=${row['total_pnl']:.2f}")

        print()
        print("  ┌─ BLOCKED QUERIES ───────────────────────────────────┐")

        # Blocked: unauthorized table
        try:
            sql_tools.execute_query("SELECT api_key FROM users")
        except SQLMCPAccessError as exc:
            print_kv("  Blocked unauthorized:", str(exc)[:70])

        # Blocked: DELETE
        try:
            sql_tools.execute_query("DELETE FROM trades WHERE pnl < 0")
        except SQLMCPAccessError as exc:
            print_kv("  Blocked DELETE:", str(exc)[:70])

        # Blocked: multi-statement
        try:
            sql_tools.execute_query("SELECT * FROM trades; DROP TABLE trades")
        except SQLMCPAccessError as exc:
            print_kv("  Blocked multi-statement:", str(exc)[:70])


def example_06_retrieval_as_tool() -> None:
    """RAG retrieval used as a tool by an agent."""
    print_header("Example 06: RAG Retrieval as a Tool")

    # Set up RAG
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    retrieval = RetrievalService(embeddings=embeddings, persist_dir=None, collection_name="demo_tools")
    ingester = DocumentIngester(embeddings, chunk_size=50, chunk_overlap=10)

    docs = [
        ("doc_eurusd", "EURUSD is the most traded forex pair. It represents the euro vs US dollar exchange rate.", {"category": "forex"}),
        ("doc_strategy", "Trend following works best in strong directional markets with low volatility. Use ATR-based stops.", {"category": "strategy"}),
        ("doc_risk", "Risk management: max 2% per trade. Always use stop losses. Diversify across uncorrelated pairs.", {"category": "risk"}),
    ]

    total_chunks = 0
    for doc_id, content, meta in docs:
        chunks = ingester.ingest(doc_id, content, meta)
        retrieval.add_chunks(chunks)
        total_chunks += len(chunks)

    print_kv("Documents ingested:", f"{len(docs)} docs → {total_chunks} chunks")

    # Use retrieval as a tool
    def search_knowledge(query: str, category: str = None, top_k: int = 3) -> dict[str, Any]:
        """Search the knowledge base (registered as a tool)."""
        results = retrieval.search(query, top_k, filter_metadata={"category": category} if category else None)
        return {
            "query": query,
            "results_count": len(results),
            "results": [{"content": r.content, "score": round(r.score, 3)} for r in results],
        }

    executor = ToolExecutor(tools={"search_knowledge": search_knowledge})

    results = executor.execute([
        ToolCall(tool_call_id="t1", tool_name="search_knowledge", parameters={"query": "forex pair trading"}),
        ToolCall(tool_call_id="t2", tool_name="search_knowledge", parameters={"query": "risk management rules", "category": "risk"}),
        ToolCall(tool_call_id="t3", tool_name="search_knowledge", parameters={"query": "cooking recipes"}),  # Should find nothing relevant
    ])

    print()
    for r in results:
        print_result(r)
        print()


def example_07_token_estimation() -> None:
    """Token estimation for tool outputs."""
    print_header("Example 07: Token Estimation")

    samples = [
        "Hello",
        "EURUSD is trading at 1.0850 with a spread of 2 pips",
        '{"bid": 1.0850, "ask": 1.0852, "spread": 2, "symbol": "EURUSD"}',
        "A" * 1000,
        "A" * 10000,
    ]

    print_kv("Token estimates (~4 chars/token):", "")
    for s in samples:
        tokens = _estimate_tokens(s)
        actual_approx = len(s) // 4
        print_kv(f"  {len(s):>6d} chars", f"≈ {tokens} tokens (approx {actual_approx})")


def example_08_cost_aware_tool_usage() -> None:
    """Cost tracking per tool call for budget management."""
    print_header("Example 08: Cost-Aware Tool Usage")

    tracker = CostTracker()

    # Simulate tool calls with different models
    tool_calls = [
        {"model": "gemini-3.1-flash-lite-preview", "input_tokens": 500, "output_tokens": 200},
        {"model": "gemini-3.1-flash-lite-preview", "input_tokens": 800, "output_tokens": 300},
        {"model": "gpt-4o", "input_tokens": 1200, "output_tokens": 500},
        {"model": "qwen2.5-coder:7b", "input_tokens": 5000, "output_tokens": 2000},
    ]

    for i, tc in enumerate(tool_calls):
        tracker.record(
            trace_id="agent-session-001",
            span_id=f"tool_call_{i+1}",
            model=tc["model"],
            input_tokens=tc["input_tokens"],
            output_tokens=tc["output_tokens"],
        )

    total = tracker.total_cost("agent-session-001")
    tokens = tracker.total_tokens("agent-session-001")
    breakdown = tracker.cost_breakdown_by_model("agent-session-001")

    print_kv("Session:", "agent-session-001")
    print_kv("Total cost:", f"${total:.6f}")
    print_kv("Total tokens:", f"input={tokens['input']}, output={tokens['output']}")
    print_kv("Entry count:", tracker.entry_count)
    print()
    print_kv("Cost breakdown:", breakdown)

    # Budget check
    budget = 0.10  # $0.10 max
    print()
    print_kv("Budget:", f"${budget:.2f}")
    print_kv("Remaining:", f"${budget - total:.6f}")
    print_kv("Within budget:", total <= budget)


def example_09_tool_call_audit() -> None:
    """Tool call audit logging for compliance."""
    print_header("Example 09: Tool Call Audit Trail")

    executor = ToolExecutor(tools={
        "get_market_price": get_market_price,
        "calculate_position_size": calculate_position_size,
    })

    calls = [
        ToolCall(tool_call_id="audit_1", tool_name="get_market_price", parameters={"symbol": "EURUSD"}),
        ToolCall(tool_call_id="audit_2", tool_name="calculate_position_size", parameters={"account_balance": 50000, "risk_pct": 0.01}),
    ]

    results = executor.execute(calls)

    # Build audit trail
    print_kv("Audit Trail:", "")
    for call, result in zip(calls, results):
        audit_entry = {
            "tool_call_id": result.tool_call_id,
            "tool_name": result.tool_name,
            "parameters": call.parameters,
            "status": "SUCCESS" if not result.is_error else "FAILURE",
            "latency_ms": result.latency_ms,
            "token_count": result.token_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print_kv(f"  [{audit_entry['tool_call_id']}]", {
            "tool": audit_entry["tool_name"],
            "status": audit_entry["status"],
            "latency": f"{audit_entry['latency_ms']}ms",
            "tokens": audit_entry["token_count"],
            "time": audit_entry["timestamp"][:19],
        })


def example_10_react_migration_path() -> None:
    """Migration path: from regex ReAct to structured tool calling."""
    print_header("Example 10: ReAct → Tool Calling Migration")

    print("  BEFORE (Regex ReAct):")
    print("    Thought: I need to check the current EURUSD price")
    print("    Action: get_market_price(EURUSD)")
    print("    Observation: 1.0850")
    print("    → Regex parsing: fragile, breaks on format changes")
    print()
    print("  AFTER (Structured Tool Calling):")

    executor = ToolExecutor(tools={
        "get_market_price": get_market_price,
        "calculate_position_size": calculate_position_size,
    })

    # Agent loop simulation
    conversation = []
    tool_calls = [
        ToolCall(tool_call_id="step_1", tool_name="get_market_price", parameters={"symbol": "EURUSD"}),
    ]

    results = executor.execute(tool_calls)
    for call, result in zip(tool_calls, results):
        conversation.append({
            "role": "assistant",
            "type": "tool_call",
            "tool": call.tool_name,
            "parameters": call.parameters,
        })
        conversation.append({
            "role": "tool",
            "type": "tool_result",
            "tool_call_id": result.tool_call_id,
            "output": json.loads(result.output) if not result.is_error else {"error": result.error},
        })

    for entry in conversation:
        if entry["type"] == "tool_call":
            print_kv(f"    🤖 Tool Call:", f"{entry['tool']}({entry['parameters']})")
        else:
            print_kv(f"    🔧 Tool Result:", entry["output"])

    print()
    print("  Benefits:")
    print("    ✅ Structured ToolCall/ToolResult contracts")
    print("    ✅ Pre-execution parameter validation")
    print("    ✅ Batch tool execution")
    print("    ✅ Error handling with is_error flag")
    print("    ✅ Token count and latency tracking")
    print("    ✅ Output size limits prevent context overflow")


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("#" * 78)
    print("#  Tool-Using Agents — Native Function Calling Examples")
    print("#  Replaces regex-based ReAct with structured ToolCall/ToolResult")
    print("#" * 78)

    examples = [
        example_01_tool_call_models,
        example_02_tool_executor,
        example_03_pre_execution_validation,
        example_04_tool_output_limits,
        example_05_sql_tool_with_validation,
        example_06_retrieval_as_tool,
        example_07_token_estimation,
        example_08_cost_aware_tool_usage,
        example_09_tool_call_audit,
        example_10_react_migration_path,
    ]

    for example_fn in examples:
        try:
            example_fn()
        except Exception as exc:
            import traceback
            print(f"\n  ERROR in {example_fn.__name__}: {exc}")
            traceback.print_exc()

    print()
    print("#" * 78)
    print("#  All tool-using examples complete!")
    print("#  ToolCall + ToolResult + ToolExecutor + ToolValidator = production-ready")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()
