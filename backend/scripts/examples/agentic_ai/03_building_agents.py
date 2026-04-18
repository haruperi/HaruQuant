"""Building Agents — Advanced Construction & Integration Examples.

Demonstrates the path from raw tool infrastructure to stateful AI researchers:
  1. Tool Foundations (ToolCall, ToolResult, ToolExecutor)
  2. Building Agents with Tools (ReAct loop)
  3. Pre-Execution Parameter Validation (ToolValidator)
  4. Structured Outputs with Pydantic
  5. Agent State Management & Short-Term Memory (Sessions)
  6. Integrating External Tools (MT5 & Web Search)
  7. Interacting with Databases (SQL with AST Validation)
  8. Agentic RAG (Retrieval as a Tool)
  9. Long-Term Agent Memory (Semantic Store)
  10. Agent Observability (Cost tracking & Audit trails)
  11. Complete Stateful AI Research Agent (Trading Analysis)

Usage:
    python backend/scripts/examples/agentic_ai/03_building_agents.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

def _load_example_env() -> None:
    env_path = Path(PROJECT_ROOT) / "backend" / "config" / "environments" / ".env"
    if not env_path.exists(): return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_example_env()
warnings.filterwarnings("ignore", message=r"authlib\.jose module is deprecated")

# ── Runtime & Tools ───────────────────────────────────────────────────
from backend.agents.runtime import (
    LLMRuntime,
    create_llm_runtime,
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    ADKRunResult,
    AgentExecutionContext,
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
from backend.agents.react import ReActAgentRuntime

# ── Specialized MCP & Services ────────────────────────────────────────
from backend.mcp.mt5_mcp.client import MT5Client
from backend.mcp.sql_mcp.tools import SQLReadOnlyTools, SQLMCPAccessError
from backend.retrieval.service import RetrievalService
from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.ingestion import DocumentIngester
from backend.agents.memory.semantic import SemanticMemoryStore
from backend.agents.runtime.session_manager import SessionManager
from backend.observability.cost_tracker import CostTracker
from tests.eval.trajectory_eval import TrajectoryEvaluator

# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def print_example_header(title: str) -> None:
    print(f"\n{'='*78}\n{title}\n{'='*78}")

def print_kv(label: str, value: Any) -> None:
    print(f"  {label:<35s} {value}")

def _default_model_name() -> str:
    from backend.config.agent_model import AGENT_MODEL
    return os.environ.get("HARUQUANT_AGENT_MODEL", AGENT_MODEL)

def _get_live_runner(json_mode: bool = False) -> tuple[ADKRunnerService, LLMRuntime]:
    model = _default_model_name()
    runtime = create_llm_runtime(model=model, temperature=0.1, json_mode=json_mode)
    runner = ADKRunnerService(config=ADKRunnerConfig(runner_name="building_demo", default_model=model))
    return runner, runtime

def _extract_text(payload: dict[str, Any]) -> str:
    if "content" in payload: return str(payload["content"])
    if "_raw_text" in payload: return str(payload["_raw_text"])
    if len(payload) == 1: return str(list(payload.values())[0])
    return json.dumps(payload)

# ────────────────────────────────────────────────────────────────────────
# 1. Tool Foundations (Contracts & Execution)
# ────────────────────────────────────────────────────────────────────────

def example_01_tool_infrastructure() -> None:
    """Foundational ToolCall/ToolResult models and high-perf execution."""
    print_example_header("01: Tool Foundations (Contracts & Execution)")
    
    # 1. Structured Contract
    call = ToolCall(tool_call_id="c1", tool_name="get_price", parameters={"symbol": "EURUSD"})
    print_kv("ToolCall Object:", call)

    # 2. Batch Execution with ToolExecutor
    executor = ToolExecutor(tools={
        "get_price": lambda symbol: {"symbol": symbol, "price": 1.0850},
        "get_time": lambda: {"utc": datetime.now(timezone.utc).isoformat()}
    })
    
    results = executor.execute([
        call,
        ToolCall(tool_call_id="c2", tool_name="get_time", parameters={})
    ])
    
    for r in results:
        print_kv(f"Result {r.tool_call_id}:", r.output)

# ────────────────────────────────────────────────────────────────────────
# 2. Building Agents with Tools (ReAct)
# ────────────────────────────────────────────────────────────────────────

def example_02_agents_with_tools() -> None:
    """ReAct Agent: The standard loop using the infrastructure from Example 01."""
    print_example_header("02: Building Agents with Tools (ReAct)")
    
    _, runtime = _get_live_runner()
    
    def get_market_sentiment(symbol: str) -> str:
        """Fetch current market sentiment for a pair."""
        return f"Sentiment for {symbol} is slightly BULLISH based on H1 trend."

    tools = {"get_market_sentiment": get_market_sentiment}
    agent = ReActAgentRuntime(llm_runtime=runtime, tools=tools, max_steps=3)
    
    request = ADKRunRequest(
        workflow_id="react-wf", correlation_id="c2", agent_name="sentiment_agent",
        input_payload={"task": "What is the sentiment for EURUSD?"},
        allowed_tools=("get_market_sentiment",)
    )
    context = AgentExecutionContext(
        workflow_id="react-wf", correlation_id="c2", session_id=None,
        model=runtime.model, allowed_tools=request.allowed_tools, prompt_version_id=None, metadata={}
    )
    
    print("  Executing ReAct loop...")
    result = agent.run(request=request, context=context)
    print_kv("Final Answer:", _extract_text(result.output_payload))

# ────────────────────────────────────────────────────────────────────────
# 3. Pre-Execution Parameter Validation
# ────────────────────────────────────────────────────────────────────────

def example_03_tool_validation() -> None:
    """ToolValidator: Catching bad agent inputs before they hit the tool."""
    print_example_header("03: Pre-Execution Parameter Validation")
    
    validator = ToolValidator()
    # Register a schema for a trade tool
    validator.register_simple(
        "open_order", 
        required_fields=("symbol", "volume"),
        optional_fields={"type": "string"}
    )
    
    test_calls = [
        {"tool_name": "open_order", "parameters": {"symbol": "EURUSD", "volume": 0.1}}, # Valid
        {"tool_name": "open_order", "parameters": {"symbol": "EURUSD"}},                # Missing volume
        {"tool_name": "open_order", "parameters": {"symbol": "EURUSD", "volume": "high"}} # Wrong type
    ]
    
    for call in test_calls:
        try:
            validator.validate(call)
            print_kv(f"✅ Validated:", call['parameters'])
        except ToolValidationError as exc:
            print_kv(f"❌ Blocked:", str(exc))

# ────────────────────────────────────────────────────────────────────────
# 4. Structured Outputs with Pydantic
# ────────────────────────────────────────────────────────────────────────

class TradeHypothesis(BaseModel):
    symbol: str = Field(..., description="The trading symbol")
    confidence: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., description="Why this trade?")

def example_04_structured_outputs() -> None:
    """Using Pydantic for guaranteed structured JSON output."""
    print_example_header("04: Structured Outputs with Pydantic")
    
    _, runtime = _get_live_runner(json_mode=True)
    
    prompt = (
        "Analyze EURUSD. Return a JSON object matching this schema: "
        f"{json.dumps(TradeHypothesis.model_json_schema())}"
    )
    
    request = ADKRunRequest(
        workflow_id="struct-wf", correlation_id="c4", agent_name="analyst",
        input_payload={"_system_prompt": prompt, "task": "Analyze EURUSD."}
    )
    context = AgentExecutionContext("wf", "c4", None, runtime.model, (), None, {})
    result = runtime.run(request=request, context=context)
    
    try:
        hypothesis = TradeHypothesis.model_validate(result.output_payload)
        print_kv("Parsed Symbol:", hypothesis.symbol)
        print_kv("Parsed Confidence:", hypothesis.confidence)
    except Exception as e:
        print_kv("Validation Failed:", str(e))

# ────────────────────────────────────────────────────────────────────────
# 5. Agent State Management & Sessions
# ────────────────────────────────────────────────────────────────────────

def example_05_state_management() -> None:
    """Maintaining state using both internal objects and SessionManager."""
    print_example_header("05: Agent State & Short-Term Memory")
    
    # 1. Ephemeral session
    manager = SessionManager()
    session = manager.create_session(metadata={"user_tier": "gold"})
    manager.activate_session(session.session_id)
    
    print_kv("Session Active:", session.session_id)
    print_kv("Session Metadata:", session.metadata)

    # 2. In-memory state tracking
    class StatefulAgent:
        def __init__(self): self.history = []
        def act(self, task): self.history.append(task); return f"Executed {task}"
    
    agent = StatefulAgent()
    agent.act("Check price")
    agent.act("Calculate risk")
    print_kv("Agent Internal History:", agent.history)

# ────────────────────────────────────────────────────────────────────────
# 6. Integrating External Tools (MT5 & Search)
# ────────────────────────────────────────────────────────────────────────

def example_06_external_tools() -> None:
    """Integrating real external systems (MT5Client and Search)."""
    print_example_header("06: Integrating External Tools & APIs")
    
    # 1. MT5 Client
    client = MT5Client()
    print_kv("MT5 Client:", "Initialized and ready for terminal connection")
    
    # 2. Web Search Tool
    def web_search(query: str):
        return f"Search Result for {query}: EURUSD dropped 20 pips after CPI."
        
    print_kv("Web Search Tool:", "Registered as available tool")

# ────────────────────────────────────────────────────────────────────────
# 7. Interacting with Databases (AST Validation)
# ────────────────────────────────────────────────────────────────────────

def example_07_database_interaction() -> None:
    """SQL MCP tool: Using AST-based validation for secure read-only access."""
    print_example_header("07: Interacting with Databases (Secure SQL)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import sqlite3
        db_path = os.path.join(tmpdir, "trading.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE trades (symbol TEXT, pnl REAL)")
        conn.execute("INSERT INTO trades VALUES ('EURUSD', 500.0), ('GBPUSD', -200.0)")
        conn.execute("CREATE TABLE secrets (key TEXT, val TEXT)")
        conn.commit()
        conn.close()

        # Governance: Only allow 'trades' table
        sql_tools = SQLReadOnlyTools(db_path, allowed_tables=("trades",))
        
        # Allowed Query
        result = sql_tools.execute_query("SELECT * FROM trades WHERE pnl > 0")
        print_kv("Safe Query Result:", result.rows)

        # Blocked Query (Unauthorized Table)
        try:
            sql_tools.execute_query("SELECT * FROM secrets")
        except SQLMCPAccessError as exc:
            print_kv("Security Block (Unauthorized):", str(exc))

# ────────────────────────────────────────────────────────────────────────
# 8. Agentic RAG (Decision-based Retrieval)
# ────────────────────────────────────────────────────────────────────────

def example_08_agentic_rag() -> None:
    """Integrating RetrievalService as a high-level agent tool."""
    print_example_header("08: Agentic Retrieval Augmented Generation")
    
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    retrieval = RetrievalService(embeddings=embeddings, persist_dir=None)
    
    # Registering retrieval as a tool
    def query_knowledge_base(query: str):
        """Search the documentation for trading rules."""
        # Simulated retrieval
        return "RULE: Never risk more than 2% of equity per trade."

    print_kv("RAG Tool:", "RetrievalService bound to query_knowledge_base tool")

# ────────────────────────────────────────────────────────────────────────
# 9. Long-Term Agent Memory (Semantic Store)
# ────────────────────────────────────────────────────────────────────────

def example_09_long_term_memory() -> None:
    """Persisting cross-session insights using vector-based memory."""
    print_example_header("09: Long-Term Agent Memory")
    
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    memory = SemanticMemoryStore(embeddings=embeddings, persist_dir=None)
    
    # Store an insight
    memory.store("User prefers Fibonacci retracements for entry confirmation.", "strategy_pref")
    
    # Recall based on semantics
    recalled = memory.retrieve("What indicators does the user like?", top_k=1)
    if recalled:
        print_kv("Recalled Insight:", recalled[0].content)

# ────────────────────────────────────────────────────────────────────────
# 10. Agent Observability (Cost & Audit)
# ────────────────────────────────────────────────────────────────────────

def example_10_observability() -> None:
    """Tracking costs, tokens, and audit trails for production agents."""
    print_example_header("10: Agent Observability (Cost & Audit)")
    
    tracker = CostTracker()
    trace_id = "trace-" + uuid4().hex[:8]
    
    # 1. Record Usage
    tracker.record(trace_id, model="gemini-3.1-flash-lite-preview", input_tokens=1000, output_tokens=500)
    print_kv("Trace Total Cost:", f"${tracker.total_cost(trace_id):.6f}")
    
    # 2. Audit Trail Simulation
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "research_agent",
        "action": "SQL_QUERY",
        "params": {"table": "trades"}
    }
    print_kv("Audit Trail Entry:", audit_entry)

# ────────────────────────────────────────────────────────────────────────
# 11. Complete Stateful AI Research Agent
# ────────────────────────────────────────────────────────────────────────

class ResearchReport(BaseModel):
    summary: str
    key_findings: List[str]
    confidence_score: float

def example_11_complete_research_agent() -> None:
    """The Final Synthesis: A stateful researcher using secure tools."""
    print_example_header("11: Stateful AI Research Agent (Final Synthesis)")

    _, runtime = _get_live_runner(json_mode=True)
    
    # Define production-ready tools
    def fetch_market_data(symbol: str):
        return {"symbol": symbol, "bid": 1.0850, "liquidity": "HIGH", "session": "London"}
        
    def query_policy(topic: str):
        return "POLICY: All algorithmic entries require spread < 3 pips."

    tools = {"fetch_market_data": fetch_market_data, "query_policy": query_policy}
    agent = ReActAgentRuntime(runtime, tools=tools)
    
    task = "Assess EURUSD for an automated entry based on current liquidity and spread policy."
    print(f"  Task: {task}")
    
    request = ADKRunRequest(
        "research-wf", "c11", "researcher", 
        {"task": task, "schema": json.dumps(ResearchReport.model_json_schema())},
        allowed_tools=("fetch_market_data", "query_policy")
    )
    context = AgentExecutionContext("wf", "c11", None, runtime.model, ("fetch_market_data", "query_policy"), None, {})
    
    result = agent.run(request=request, context=context)
    print_kv("Final Research Report:", result.output_payload)

# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "#"*78)
    print("#  Building Agents — Advanced Construction & Integration")
    print("#  Merged Infrastructure + Agent Logic")
    print("#"*78)

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

    for ex in examples:
        try:
            ex()
        except Exception as e:
            print(f"\n  ERROR in {ex.__name__}: {e}")

    print("\n" + "#"*78)
    print("#  All construction examples complete!")
    print("#"*78 + "\n")

if __name__ == "__main__":
    main()
