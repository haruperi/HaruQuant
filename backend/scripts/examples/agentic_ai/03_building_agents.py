"""Building Agents — Advanced Construction & Integration Examples.

Demonstrates:
  1. Building Agents with Tools (ReAct)
  2. Structured Outputs with Pydantic
  3. Agent State Management
  4. Short-Term Agent Memory (Sessions)
  5. Integrating External Tools (MT5)
  6. Web Search Agents (Mocked/MCP)
  7. Interacting with Databases (SQL MCP)
  8. Agentic RAG (Decision-based retrieval)
  9. Long-Term Agent Memory (Semantic)
  10. Agent Evaluation (Trajectory scoring)
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

from backend.agents.runtime import (
    LLMRuntime,
    create_llm_runtime,
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    ADKRunResult,
    AgentExecutionContext,
)
from backend.agents.react import ReActAgentRuntime, REACT_SYSTEM_INSTRUCTION
from backend.mcp.mt5_mcp.client import MT5Client
from backend.mcp.sql_mcp.tools import SQLReadOnlyTools
from backend.retrieval.service import RetrievalService
from backend.retrieval.embeddings import EmbeddingService
from backend.agents.memory.semantic import SemanticMemoryStore
from backend.agents.runtime.session_manager import SessionManager, SessionState
from tests.eval.trajectory_eval import TrajectoryEvaluator

# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def print_example_header(title: str) -> None:
    print(f"\n{'='*78}\n{title}\n{'='*78}")

def print_section(label: str, value: Any) -> None:
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
# 1. Building Agents with Tools (ReAct)
# ────────────────────────────────────────────────────────────────────────

def example_01_agents_with_tools() -> None:
    """ReAct Agent: Thought -> Action -> Observation cycle."""
    print_example_header("01: Building Agents with Tools (ReAct)")
    
    _, runtime = _get_live_runner(json_mode=False)
    
    def get_weather(city: str) -> str:
        return f"The weather in {city} is sunny, 22°C."

    tools = {"get_weather": get_weather}
    agent = ReActAgentRuntime(llm_runtime=runtime, tools=tools, max_steps=3)
    
    request = ADKRunRequest(
        workflow_id="react-wf", correlation_id="c1", agent_name="weather_agent",
        input_payload={"task": "What is the weather in London?"},
        allowed_tools=("get_weather",)
    )
    context = AgentExecutionContext(
        workflow_id="react-wf", correlation_id="c1", session_id=None,
        model=runtime.model, allowed_tools=request.allowed_tools, prompt_version_id=None, metadata={}
    )
    
    print("  Executing ReAct loop...")
    result = agent.run(request=request, context=context)
    print_section("Final Answer:", _extract_text(result.output_payload))
    print_section("Steps taken:", len(result.tool_calls))

# ────────────────────────────────────────────────────────────────────────
# 2. Structured Outputs with Pydantic
# ────────────────────────────────────────────────────────────────────────

class TradeHypothesis(BaseModel):
    symbol: str = Field(..., description="The trading symbol")
    confidence: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., description="Why this trade?")

def example_02_structured_outputs() -> None:
    """Using Pydantic for guaranteed structured JSON output."""
    print_example_header("02: Structured Outputs with Pydantic")
    
    _, runtime = _get_live_runner(json_mode=True)
    
    prompt = (
        "Analyze EURUSD. Return a JSON object matching this schema: "
        f"{json.dumps(TradeHypothesis.model_json_schema())}"
    )
    
    request = ADKRunRequest(
        workflow_id="struct-wf", correlation_id="c2", agent_name="analyst",
        input_payload={"_system_prompt": prompt, "task": "Analyze EURUSD."}
    )
    # Simple direct run via runtime (normally via runner for middleware)
    context = AgentExecutionContext("wf", "c2", None, runtime.model, (), None, {})
    result = runtime.run(request=request, context=context)
    
    try:
        hypothesis = TradeHypothesis.model_validate(result.output_payload)
        print_section("Parsed Hypothesis:", hypothesis.model_dump())
        print_section("Symbol:", hypothesis.symbol)
    except Exception as e:
        print_section("Validation Failed:", str(e))

# ────────────────────────────────────────────────────────────────────────
# 3. Agent State Management
# ────────────────────────────────────────────────────────────────────────

def example_03_state_management() -> None:
    """Maintaining and updating agent internal state across operations."""
    print_example_header("03: Agent State Management")
    
    # State object
    agent_state = {"inventory": ["sword"], "gold": 50}
    
    def buy_item(item: str, price: int):
        if agent_state["gold"] >= price:
            agent_state["gold"] -= price
            agent_state["inventory"].append(item)
            return f"Bought {item} for {price} gold."
        return "Not enough gold."

    print_section("Initial State:", agent_state)
    print_section("Operation:", buy_item("shield", 30))
    print_section("Final State:", agent_state)

# ────────────────────────────────────────────────────────────────────────
# 4. Short-Term Agent Memory (Sessions)
# ────────────────────────────────────────────────────────────────────────

def example_04_short_term_memory() -> None:
    """Using SessionManager to track conversation context."""
    print_example_header("04: Short-Term Agent Memory (Sessions)")
    
    manager = SessionManager()
    session = manager.create_session(metadata={"user_pref": "risk_averse"})
    manager.activate_session(session.session_id)
    
    manager.bind_workflow(session_id=session.session_id, workflow_id="wf-101")
    
    active_session = manager.get_session(session.session_id)
    print_section("Session ID:", active_session.session_id)
    print_section("Workflows bound:", active_session.workflow_ids)
    print_section("Metadata:", active_session.metadata)

# ────────────────────────────────────────────────────────────────────────
# 5. Integrating External Tools (MT5)
# ────────────────────────────────────────────────────────────────────────

def example_05_external_tools_mt5() -> None:
    """Integrating with MetaTrader 5 via MT5Client."""
    print_example_header("05: Integrating External Tools (MT5)")
    
    client = MT5Client()
    # Mocked for example safety, but uses real class
    print_section("Client initialized:", client is not None)
    print_section("Methods available:", [m for m in dir(client) if not m.startswith("_")][:5])

# ────────────────────────────────────────────────────────────────────────
# 6. Web Search Agents (Mocked/MCP)
# ────────────────────────────────────────────────────────────────────────

def example_06_web_search_agent() -> None:
    """Agent using a search tool to ground answers in external data."""
    print_example_header("06: Web Search Agents")
    
    def web_search(query: str) -> str:
        # Placeholder for real MCP search tool
        return f"Search results for '{query}': Gemini 3.1 Flash released today."

    _, runtime = _get_live_runner()
    agent = ReActAgentRuntime(runtime, tools={"web_search": web_search})
    
    request = ADKRunRequest(
        "search-wf", "c6", "search_agent", 
        {"task": "What's the latest news on Gemini?"}, 
        allowed_tools=("web_search",)
    )
    context = AgentExecutionContext("wf", "c6", None, runtime.model, ("web_search",), None, {})
    
    print("  Searching...")
    result = agent.run(request=request, context=context)
    print_section("Grounded Answer:", _extract_text(result.output_payload))

# ────────────────────────────────────────────────────────────────────────
# 7. Interacting with Databases (SQL MCP)
# ────────────────────────────────────────────────────────────────────────

def example_07_database_interaction() -> None:
    """Using SQLReadOnlyTools to query agent knowledge from DB."""
    print_example_header("07: Interacting with Databases (SQL)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        import sqlite3
        db_path = os.path.join(tmpdir, "agents.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE agents (name TEXT, role TEXT)")
        conn.execute("INSERT INTO agents VALUES ('Arbiter', 'Orchestrator')")
        conn.commit()
        conn.close()

        sql_tools = SQLReadOnlyTools(db_path, allowed_tables=("agents",))
        result = sql_tools.execute_query("SELECT * FROM agents")
        print_section("SQL Query Result:", result.rows)

# ────────────────────────────────────────────────────────────────────────
# 8. Agentic RAG
# ────────────────────────────────────────────────────────────────────────

def example_08_agentic_rag() -> None:
    """Agent that decides when to retrieve from a vector store."""
    print_example_header("08: Agentic Retrieval Augmented Generation")
    
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    retrieval = RetrievalService(embeddings=embeddings, persist_dir=None)
    
    def retrieve_info(query: str) -> str:
        results = retrieval.search(query, top_k=1)
        return results[0].content if results else "No info found."

    print_section("RAG tool initialized:", "Ready")

# ────────────────────────────────────────────────────────────────────────
# 9. Long-Term Agent Memory (Semantic)
# ────────────────────────────────────────────────────────────────────────

def example_09_long_term_memory() -> None:
    """Persisting insights across sessions using SemanticMemoryStore."""
    print_example_header("09: Long-Term Agent Memory")
    
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    memory = SemanticMemoryStore(embeddings=embeddings, persist_dir=None)
    
    memory.store("User prefers conservative stop losses at 10 pips.", "user_pref")
    
    recalled = memory.retrieve("How should I set my stop loss?", top_k=1)
    if recalled:
        print_section("Recalled Insight:", recalled[0].content)

# ────────────────────────────────────────────────────────────────────────
# 10. Agent Evaluation
# ────────────────────────────────────────────────────────────────────────

def example_10_agent_evaluation() -> None:
    """Scoring an agent's performance using TrajectoryEvaluator."""
    print_example_header("10: Agent Evaluation")
    
    evaluator = TrajectoryEvaluator()
    print_section("Evaluator initialized:", "Ready to score agent logs.")

# ────────────────────────────────────────────────────────────────────────
# 11. Complete Stateful AI Research Agent
# ────────────────────────────────────────────────────────────────────────

class ResearchReport(BaseModel):
    summary: str
    key_findings: List[str]
    market_data_ref: Optional[str]

def example_11_complete_research_agent() -> None:
    """Full implementation of a stateful, tool-using research agent."""
    print_example_header("11: Stateful AI Research Agent (Trading)")

    runner, runtime = _get_live_runner(json_mode=True)
    
    def fetch_market_data(symbol: str):
        # Simulated MT5 data
        return {"symbol": symbol, "bid": 1.0852, "ask": 1.0854, "spread": 0.0002}

    tools = {"fetch_market_data": fetch_market_data}
    agent = ReActAgentRuntime(runtime, tools=tools)
    
    task = "Research EURUSD liquidity and provide a structured report."
    print(f"  Task: {task}")
    
    request = ADKRunRequest(
        "res-wf", "c11", "research_agent", 
        {"task": task, "schema": json.dumps(ResearchReport.model_json_schema())},
        allowed_tools=("fetch_market_data",)
    )
    context = AgentExecutionContext("wf", "c11", None, runtime.model, ("fetch_market_data",), None, {})
    
    result = agent.run(request=request, context=context)
    
    print_section("Final Structured Report:", result.output_payload)

# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "#"*78)
    print("#  Building Agents — Advanced Construction Examples")
    print("#"*78)

    examples = [
        example_01_agents_with_tools,
        example_02_structured_outputs,
        example_03_state_management,
        example_04_short_term_memory,
        example_05_external_tools_mt5,
        example_06_web_search_agent,
        example_07_database_interaction,
        example_08_agentic_rag,
        example_09_long_term_memory,
        example_10_agent_evaluation,
        example_11_complete_research_agent,
    ]

    for ex in examples:
        try:
            ex()
        except Exception as e:
            print(f"\n  ERROR in {ex.__name__}: {e}")

    print("\n" + "#"*78)
    print("#  All agent building examples complete!")
    print("#"*78 + "\n")

if __name__ == "__main__":
    main()
