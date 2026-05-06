"""Building agents with HaruQuant-native tools and contracts.

Usage:
    python scripts/examples/agentic_ai/03_building_agents.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CONTRACTS_ROOT = Path(PROJECT_ROOT) / "contracts"
WORKFLOWS_ROOT = Path(PROJECT_ROOT) / "config" / "workflows"
SCRATCH_ROOT = Path(PROJECT_ROOT) / ".tmp_agentic_examples"
SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)

from agents.react import ReActAgentRuntime
from agents.runtime import (
    ADKRunRequest,
    AgentExecutionContext,
    ToolCall,
    ToolExecutor,
)
from agents.runtime.llm_runtime import LLMRuntime
from agents.runtime.session_manager import SessionManager
from agents.runtime.tool_validation import ToolValidationError, ToolValidator, register_mcp_schemas
from services.data.mt5.tools import MT5ReadOnlyTools
from services.data.sql_tools import SQLMCPAccessError, SQLReadOnlyTools
from observability.cost_tracker import CostTracker


def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2, default=str)
    print(f"  {label:<35s} {value}")


def load_workflow(name: str) -> dict[str, Any]:
    path = WORKFLOWS_ROOT / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_contract_example(contract_name: str, sample_name: str) -> dict[str, Any]:
    path = CONTRACTS_ROOT / contract_name / "examples" / "valid" / f"{sample_name}.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def summarize_contract(payload: dict[str, Any]) -> dict[str, Any]:
    body = payload.get("payload", {})
    summary = {
        "contract_type": payload.get("contract_type"),
        "originator": payload.get("originator", {}).get("id"),
        "payload_keys": sorted(body.keys()),
    }
    if "symbol" in body:
        summary["symbol"] = body["symbol"]
    return summary


@dataclass(frozen=True)
class FakeMT5Gateway:
    """Deterministic MT5 gateway for runnable examples."""

    def account_info(self) -> dict[str, Any]:
        return {
            "balance": 100_000.0,
            "equity": 100_640.0,
            "margin_free": 92_500.0,
            "currency": "USD",
        }

    def positions_get(self) -> list[dict[str, Any]]:
        return [
            {"symbol": "EURUSD", "volume": 0.20, "profit": 120.0, "ticket": 7001},
            {"symbol": "XAUUSD", "volume": 0.10, "profit": -35.0, "ticket": 7002},
        ]

    def orders_get(self) -> list[dict[str, Any]]:
        return [
            {"symbol": "EURUSD", "type": "BUY_LIMIT", "price": 1.0845, "ticket": 8101},
        ]

    def symbol_info(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "bid": 1.0846,
            "ask": 1.0848,
            "spread_points": 12,
            "session": "london",
        }

    def get_ticks(self, symbol: str, count: int = 100, as_dataframe: bool = True) -> list[dict[str, Any]]:
        return [
            {"symbol": symbol, "bid": 1.0845, "ask": 1.0847, "time": "2026-04-08T10:20:00Z"},
            {"symbol": symbol, "bid": 1.0846, "ask": 1.0848, "time": "2026-04-08T10:20:01Z"},
            {"symbol": symbol, "bid": 1.0846, "ask": 1.0848, "time": "2026-04-08T10:20:02Z"},
        ][:count]


class MockLLMRuntime(LLMRuntime):
    """Small deterministic LLM runtime for ReAct examples."""

    def __init__(self, responses: list[str]) -> None:
        super().__init__(model="mock-react")
        self._responses = responses
        self._index = 0

    def _call_llm(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        if self._index < len(self._responses):
            content = self._responses[self._index]
            self._index += 1
        else:
            content = self._responses[-1]
        return {
            "content": content,
            "prompt_tokens": 120,
            "completion_tokens": 60,
            "total_tokens": 180,
        }


def build_tool_registry() -> dict[str, Any]:
    mt5_tools = MT5ReadOnlyTools(gateway=FakeMT5Gateway())
    workflow = load_workflow("proposal")

    def get_symbol_info(symbol: str) -> dict[str, Any]:
        """Read broker-derived symbol metadata from the MT5 tool facade."""
        return mt5_tools.get_symbol_info(symbol)

    def get_ticks(symbol: str, count: int = 3) -> dict[str, Any]:
        """Fetch recent broker ticks through HaruQuant's MT5 read tools."""
        return mt5_tools.get_ticks(symbol=symbol, count=count)

    def get_account_info() -> dict[str, Any]:
        """Return account state used during proposal and risk review."""
        return mt5_tools.get_account_info()

    def list_positions() -> list[dict[str, Any]]:
        """List open positions available to research and compliance agents."""
        return mt5_tools.list_positions()

    def get_policy_snapshot(topic: str) -> dict[str, Any]:
        """Retrieve policy and workflow guidance from local HaruQuant artifacts."""
        stage_map = {step["name"]: step["agent"] for step in workflow["steps"]}
        return {
            "topic": topic,
            "workflow": workflow["name"],
            "stage_owner_map": stage_map,
            "note": "proposal workflow requires risk review before approval_decision and execution",
        }

    return {
        "get_symbol_info": get_symbol_info,
        "get_ticks": get_ticks,
        "get_account_info": get_account_info,
        "list_positions": list_positions,
        "get_policy_snapshot": get_policy_snapshot,
    }


class TradeReviewSummary(BaseModel):
    symbol: str = Field(..., description="The symbol under review.")
    readiness_state: str = Field(..., description="Current proposal readiness state.")
    next_agent: str = Field(..., description="Next HaruQuant agent expected to act.")


def example_01_tool_infrastructure() -> None:
    """Show ToolCall and ToolExecutor with real HaruQuant tool names."""
    print_example_header("01: Tool Infrastructure with HaruQuant Tool Names")

    tools = build_tool_registry()
    executor = ToolExecutor(tools=tools)
    calls = [
        ToolCall(tool_call_id="tool-1", tool_name="get_symbol_info", parameters={"symbol": "EURUSD"}),
        ToolCall(tool_call_id="tool-2", tool_name="get_account_info", parameters={}),
    ]
    results = executor.execute(calls)
    for result in results:
        print_kv(f"Result {result.tool_call_id}", result.output)


def example_02_agents_with_tools() -> None:
    """Run ReAct against HaruQuant-native tools with a deterministic runtime."""
    print_example_header("02: ReAct Agent over HaruQuant Tools")

    tools = build_tool_registry()
    llm = MockLLMRuntime(
        [
            'Thought: I need broker context first.\nAction: get_symbol_info({"symbol": "EURUSD"})',
            'Thought: I should verify microstructure and freshness.\nAction: get_ticks({"symbol": "EURUSD", "count": 2})',
            (
                'Thought: I have enough context.\nFinal: '
                '{"summary":"EURUSD spread is within the proposal envelope and recent ticks are fresh.",'
                '"next_step":"draft_or_review_trade_hypothesis","symbol":"EURUSD"}'
            ),
        ]
    )
    agent = ReActAgentRuntime(llm_runtime=llm, tools=tools, max_steps=4)

    request = ADKRunRequest(
        workflow_id="react-proposal",
        correlation_id="react-01",
        agent_name="research_agent",
        input_payload={"task": "Review EURUSD market state before drafting a proposal."},
        allowed_tools=("get_symbol_info", "get_ticks"),
    )
    context = AgentExecutionContext(
        workflow_id="react-proposal",
        correlation_id="react-01",
        session_id=None,
        model="mock-react",
        allowed_tools=request.allowed_tools,
        prompt_version_id=None,
        metadata={},
    )
    result = agent.run(request=request, context=context)
    print_kv("Final payload", result.output_payload)
    print_kv("ReAct steps", len(agent.step_log))


def example_03_tool_validation() -> None:
    """Validate real tool requests before execution."""
    print_example_header("03: Tool Validation for Broker Actions")

    validator = ToolValidator()
    register_mcp_schemas(validator)
    validator.register_simple(
        "place_order",
        required_fields=("symbol", "volume_lots", "side"),
        optional_fields={"max_deviation_points": "number"},
    )

    test_calls = [
        {"tool_name": "place_order", "parameters": {"symbol": "EURUSD", "volume_lots": 0.25, "side": "buy"}},
        {"tool_name": "place_order", "parameters": {"symbol": "EURUSD", "side": "buy"}},
        {"tool_name": "place_order", "parameters": {"symbol": "EURUSD", "volume_lots": "full", "side": "buy"}},
    ]

    for call in test_calls:
        try:
            validator.validate(call)
            volume_lots = call["parameters"].get("volume_lots")
            if volume_lots is not None and not isinstance(volume_lots, (int, float)):
                raise ToolValidationError("place_order.volume_lots must be numeric for broker-safe execution")
            print_kv("Validated", call["parameters"])
        except ToolValidationError as exc:
            print_kv("Blocked", str(exc))


def example_04_structured_outputs() -> None:
    """Parse a real TradeProposal sample into an application-specific summary."""
    print_example_header("04: Structured Outputs from TradeProposal")

    proposal = load_contract_example("trade_proposal", "eurusd_ready_for_risk")
    summary = TradeReviewSummary.model_validate(
        {
            "symbol": proposal["payload"]["symbol"],
            "readiness_state": proposal["payload"]["readiness_state"],
            "next_agent": "risk_governor_agent",
        }
    )
    print_kv("Structured summary", summary.model_dump())


def example_05_state_management() -> None:
    """Keep workflow and proposal state inside a shared agent session."""
    print_example_header("05: Session State for Proposal Lifecycles")

    manager = SessionManager()
    session = manager.create_session(
        metadata={
            "workflow_name": "proposal",
            "proposal_id": "prop_01",
            "active_agents": ["strategy_agent", "research_agent", "risk_governor_agent"],
        }
    )
    manager.activate_session(session.session_id)
    session.metadata["last_contract"] = "TradeProposal"
    session.metadata["approval_state"] = "ready_for_risk"

    print_kv("Session", session.session_id)
    print_kv("Metadata", session.metadata)


def example_06_external_tools() -> None:
    """Combine broker tools, SQL reads, and local policy retrieval."""
    print_example_header("06: External Tools Bound to HaruQuant")

    tools = build_tool_registry()
    db_path = SCRATCH_ROOT / "example_06_external_tools.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE evaluation_reports (workflow_id TEXT, verdict TEXT, overall_score REAL)")
    conn.execute("INSERT INTO evaluation_reports VALUES ('wf_01', 'pass', 0.945)")
    conn.commit()
    conn.close()

    sql_tools = SQLReadOnlyTools(str(db_path), allowed_tables=("evaluation_reports",))
    print_kv("Broker symbol info", tools["get_symbol_info"]("EURUSD"))
    print_kv("Recent ticks", tools["get_ticks"]("EURUSD", count=2))
    print_kv("Policy snapshot", tools["get_policy_snapshot"]("approval_decision"))
    print_kv(
        "Evaluation report rows",
        sql_tools.execute_query("SELECT workflow_id, verdict, overall_score FROM evaluation_reports").rows,
    )


def example_07_database_interaction() -> None:
    """Use SQLReadOnlyTools against HaruQuant-like tables and access rules."""
    print_example_header("07: Database Interaction with SQLReadOnlyTools")

    db_path = SCRATCH_ROOT / "example_07_database_interaction.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE trade_proposals (proposal_id TEXT, symbol TEXT, readiness_state TEXT)")
    conn.execute("INSERT INTO trade_proposals VALUES ('prop_01', 'EURUSD', 'ready_for_risk')")
    conn.execute("CREATE TABLE secrets (key TEXT, val TEXT)")
    conn.execute("INSERT INTO secrets VALUES ('jwt', 'do-not-read')")
    conn.commit()
    conn.close()

    sql_tools = SQLReadOnlyTools(str(db_path), allowed_tables=("trade_proposals",))
    safe_rows = sql_tools.execute_query("SELECT proposal_id, symbol, readiness_state FROM trade_proposals").rows
    print_kv("Safe query", safe_rows)

    try:
        sql_tools.execute_query("SELECT * FROM secrets")
    except SQLMCPAccessError as exc:
        print_kv("Blocked query", str(exc))


def example_08_agentic_rag() -> None:
    """Retrieve local HaruQuant knowledge instead of isolated text snippets."""
    print_example_header("08: Agentic RAG over Local HaruQuant Artifacts")

    knowledge_base = {
        "proposal": load_workflow("proposal")["description"].strip(),
        "momentum_trading": load_workflow("momentum_trading")["description"].strip(),
        "trade_hypothesis": summarize_contract(load_contract_example("trade_hypothesis", "eurusd_buy")),
    }

    def query_knowledge_base(query: str) -> dict[str, Any]:
        query_lower = query.lower()
        matches = {
            key: value
            for key, value in knowledge_base.items()
            if key in query_lower or any(token in str(value).lower() for token in query_lower.split())
        }
        return matches or {"message": "no local artifact matched the query"}

    print_kv("Query result", query_knowledge_base("proposal risk review for trade_hypothesis"))


def example_09_long_term_memory() -> None:
    """Persist durable operator preferences in a simple ledger."""
    print_example_header("09: Long-Term Memory for Operator Preferences")

    memory_entries = [
        {
            "stored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "kind": "portfolio_preference",
            "content": "Operator prefers approved_with_limits outcomes over outright rejects when volatility is elevated.",
        },
        {
            "stored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "kind": "execution_preference",
            "content": "Execution agent should prefer limit_retest logic for EURUSD proposal flows.",
        },
    ]
    print_kv("Memory entries", memory_entries)


def example_10_observability() -> None:
    """Track the cost and audit story of a HaruQuant agent run."""
    print_example_header("10: Observability for Agent Runs")

    tracker = CostTracker()
    trace_id = "trace-proposal-01"
    tracker.record(trace_id, model="gemini-3.1-flash-lite-preview", input_tokens=1_250, output_tokens=620)

    audit_entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "workflow": "proposal",
        "agent": "research_agent",
        "action": "tool_call",
        "tool": "get_symbol_info",
        "symbol": "EURUSD",
    }
    print_kv("Total cost", f"${tracker.total_cost(trace_id):.6f}")
    print_kv("Audit entry", audit_entry)


def example_11_complete_research_agent() -> None:
    """Complete example: a research agent producing contract-aware output."""
    print_example_header("11: Complete Research Agent Flow")

    tools = build_tool_registry()
    llm = MockLLMRuntime(
        [
            'Thought: I need market structure.\nAction: get_symbol_info({"symbol": "EURUSD"})',
            'Thought: I should confirm portfolio context.\nAction: list_positions({})',
            (
                'Thought: The setup is ready to summarize.\nFinal: '
                '{"summary":"EURUSD remains inside the operating envelope and existing portfolio exposure is manageable.",'
                '"key_findings":["spread is 12 points","open EURUSD exposure already exists but remains modest","proposal should move to risk review"],'
                '"confidence_score":0.81}'
            ),
        ]
    )
    agent = ReActAgentRuntime(llm_runtime=llm, tools=tools, max_steps=4)
    request = ADKRunRequest(
        workflow_id="proposal-flow",
        correlation_id="proposal-11",
        agent_name="research_agent",
        input_payload={
            "task": "Prepare the market context that will accompany EURUSD proposal prop_01 into risk review."
        },
        allowed_tools=("get_symbol_info", "list_positions"),
    )
    context = AgentExecutionContext(
        workflow_id="proposal-flow",
        correlation_id="proposal-11",
        session_id=None,
        model="mock-react",
        allowed_tools=request.allowed_tools,
        prompt_version_id=None,
        metadata={"proposal_id": "prop_01"},
    )
    result = agent.run(request=request, context=context)
    print_kv("Research output", result.output_payload)
    print_kv("Related contract", summarize_contract(load_contract_example("trade_proposal", "eurusd_ready_for_risk")))


def main() -> None:
    print()
    print("#" * 78)
    print("#  Building Agents with HaruQuant Tools")
    print("#" * 78)

    examples = [
        example_01_tool_infrastructure,
        example_02_agents_with_tools,
        example_03_tool_validation,
        example_04_structured_outputs,
        example_05_state_management,
        example_06_external_tools,
        example_07_database_interaction,
        example_08_agentic_rag,
        example_09_long_term_memory,
        example_10_observability,
        example_11_complete_research_agent,
    ]

    for example in examples:
        try:
            example()
        except Exception as exc:
            print(f"\n  ERROR in {example.__name__}: {exc}")

    print()
    print("#" * 78)
    print("#  All building-agent examples complete")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()

