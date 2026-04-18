"""Multi-Agent Systems — Advanced Orchestration & Coordination.

Demonstrates:
  1. Multi-Agent Architecture (Specialized Roles)
  2. Orchestrating Agent Activities (Sequential/Parallel)
  3. Routing and Data Flow (Decision-based passing)
  4. State Management in Multi-Agent Systems (Shared Sessions)
  5. Multi-Agent Orchestration and State Coordination (Investment Committee)
  6. Multi-Agent Retrieval Augmented Generation (Collaborative RAG)
  7. Design and Build a complete multi-agent system for a real-world scenario.

Usage:
    python backend/scripts/examples/agentic_ai/04_multi_agent_systems.py
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

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
from backend.agents.runtime.workflows import (
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
    RoutingWorkflowRunner,
    RoutingWorkflowBranch,
    OrchestratorWorkerWorkflowRunner,
    OrchestratorWorkerTask,
)
from backend.agents.runtime.session_manager import SessionManager
from backend.retrieval.service import RetrievalService
from backend.retrieval.embeddings import EmbeddingService

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
    runner = ADKRunnerService(config=ADKRunnerConfig(runner_name="multi_agent_demo", default_model=model))
    return runner, runtime

def _extract_text(payload: dict[str, Any]) -> str:
    if "content" in payload: return str(payload["content"])
    if "_raw_text" in payload: return str(payload["_raw_text"])
    if len(payload) == 1: return str(list(payload.values())[0])
    return json.dumps(payload)

# ────────────────────────────────────────────────────────────────────────
# 1. Multi-Agent Architecture
# ────────────────────────────────────────────────────────────────────────

def example_01_multi_agent_architecture() -> None:
    """Defining a team of specialized agents."""
    print_example_header("01: Multi-Agent Architecture")
    
    class TradingTeam:
        RESEARCHER = "Finds market signals and trends."
        RISK_MANAGER = "Evaluates exposure and stop-loss levels."
        EXECUTOR = "Selects best order type and timing."

    print_section("Team Member 1:", f"Researcher - {TradingTeam.RESEARCHER}")
    print_section("Team Member 2:", f"Risk Manager - {TradingTeam.RISK_MANAGER}")
    print_section("Team Member 3:", f"Executor - {TradingTeam.EXECUTOR}")

# ────────────────────────────────────────────────────────────────────────
# 2. Orchestrating Agent Activities
# ────────────────────────────────────────────────────────────────────────

def example_02_orchestration() -> None:
    """Using SequentialWorkflowRunner to coordinate a pipeline."""
    print_example_header("02: Orchestrating Agent Activities")
    
    runner, runtime = _get_live_runner()
    pipeline = SequentialWorkflowRunner(runner)
    
    steps = (
        SequentialWorkflowStep(
            "market_scan", runtime, 
            ADKRunRequest("wf-scan", "c1", "analyst", {"task": "Scan top 3 FX pairs. Output pairs names only."})
        ),
        SequentialWorkflowStep(
            "pair_deep_dive", runtime, 
            ADKRunRequest("wf-scan", "c1", "researcher", {"task": "Perform deep dive on the first pair found."})
        )
    )
    
    print("  Orchestrating Scan -> Deep Dive...")
    results = pipeline.run(steps=steps)
    for res in results:
        print_section(f"Agent {res.agent_name} output:", _extract_text(res.output_payload)[:80] + "...")

# ────────────────────────────────────────────────────────────────────────
# 3. Routing and Data Flow
# ────────────────────────────────────────────────────────────────────────

def example_03_routing_data_flow() -> None:
    """Decision-based routing where one agent directs the flow."""
    print_example_header("03: Routing and Data Flow")
    
    runner, runtime = _get_live_runner()
    
    # In a real system, the 'router' would be an LLM call.
    # Here we show the implementation of the branches it could take.
    routing_runner = RoutingWorkflowRunner(runner)
    
    branches = (
        RoutingWorkflowBranch("BULLISH", runtime, ADKRunRequest("rt", "c3", "buyer", {"task": "Find buy entry"})),
        RoutingWorkflowBranch("BEARISH", runtime, ADKRunRequest("rt", "c3", "seller", {"task": "Find sell entry"}))
    )
    
    decision = "BULLISH" # Mocked decision from a prior 'Market Sentiment' agent
    print_section("Market Sentiment Decision:", decision)
    
    result = routing_runner.run(route_key=decision, branches=branches)
    print_section("Active Branch Agent:", result.agent_name)
    print_section("Task:", _extract_text(result.output_payload)[:60] + "...")

# ────────────────────────────────────────────────────────────────────────
# 4. State Management in Multi-Agent Systems
# ────────────────────────────────────────────────────────────────────────

def example_04_state_management() -> None:
    """Using a shared session to maintain state across multiple agents."""
    print_example_header("04: State Management (Shared Session)")
    
    manager = SessionManager()
    shared_session = manager.create_session(metadata={"global_risk_limit": 5000})
    
    # Agent 1 (Risk) updates the shared state
    shared_session.metadata["current_exposure"] = 1200
    print_section("Shared State (Risk Agent update):", shared_session.metadata)
    
    # Agent 2 (Compliance) reads the state
    limit = shared_session.metadata["global_risk_limit"]
    exposure = shared_session.metadata["current_exposure"]
    status = "OK" if exposure < limit else "VIOLATION"
    print_section("Compliance Check:", status)

# ────────────────────────────────────────────────────────────────────────
# 5. Multi-Agent Orchestration and State Coordination
# ────────────────────────────────────────────────────────────────────────

def example_05_orchestration_state_coordination() -> None:
    """Investment Committee: Parallel agents with shared state synthesis."""
    print_example_header("05: Multi-Agent State Coordination (Committee)")
    
    runner, runtime = _get_live_runner()
    orchestrator = OrchestratorWorkerWorkflowRunner(runner)
    
    tasks = (
        OrchestratorWorkerTask("TechAnalyst", runtime, ADKRunRequest("cm", "c5", "tech", {"task": "Analyze EURUSD RSI"})),
        OrchestratorWorkerTask("MacroAnalyst", runtime, ADKRunRequest("cm", "c5", "macro", {"task": "Check ECB news"}))
    )
    
    print("  Committee meeting in progress (Parallel Analysis)...")
    group_result = orchestrator.run(tasks=tasks)
    
    # Coordination step: Synthesis of both outputs
    print_section("Agents consulted:", list(group_result.results.keys()))
    synthesis = " | ".join([_extract_text(res.output_payload)[:50] for res in group_result.results.values()])
    print_section("Synthesized View:", synthesis + "...")

# ────────────────────────────────────────────────────────────────────────
# 6. Multi-Agent Retrieval Augmented Generation
# ────────────────────────────────────────────────────────────────────────

def example_06_multi_agent_rag() -> None:
    """Different agents querying specialized knowledge pools."""
    print_example_header("06: Multi-Agent RAG (Collaborative)")
    
    embeddings = EmbeddingService(model="all-MiniLM-L6-v2")
    # Shared retrieval service, but agents use different query strategies
    retrieval = RetrievalService(embeddings=embeddings, persist_dir=None)
    
    def agent_technical_query(symbol: str) -> str:
        # Queries for 'indicators' and 'patterns'
        return f"TECHNICAL RAG: Recalled EMA-20 trend for {symbol}"
        
    def agent_fundamental_query(symbol: str) -> str:
        # Queries for 'earnings' and 'macro'
        return f"FUNDAMENTAL RAG: Recalled ECB Interest Rate decision for {symbol}"

    print_section("Tech Agent RAG:", agent_technical_query("EURUSD"))
    print_section("Fund Agent RAG:", agent_fundamental_query("EURUSD"))

# ────────────────────────────────────────────────────────────────────────
# 7. Complete Multi-Agent Business System
# ────────────────────────────────────────────────────────────────────────

def example_07_complete_business_system() -> None:
    """Complete: Trade Approval System.
    
    Workflow:
    1. Researcher scans market.
    2. Analyst evaluates setup.
    3. Risk Governor approves or rejects.
    """
    print_example_header("07: Complete Multi-Agent Trade Approval System")
    
    runner, runtime = _get_live_runner()
    
    # 1. Define instructions for our business roles
    RESEARCH_INSTRUCTION = "You are a Market Researcher. Find a high-potential trade setup in EURUSD."
    ANALYST_INSTRUCTION = "You are a Trade Analyst. Evaluate the Researcher's setup and provide a score (1-10)."
    GOVERNOR_INSTRUCTION = "You are a Risk Governor. Approve only if score > 7. Respond with APPROVED or REJECTED."

    workflow = SequentialWorkflowRunner(runner)
    workflow_id = f"biz-{uuid4().hex[:4]}"
    
    steps = (
        SequentialWorkflowStep("research", runtime, ADKRunRequest(workflow_id, "c7", "researcher", {"_system_prompt": RESEARCH_INSTRUCTION, "task": "Search for EURUSD setup"})),
        SequentialWorkflowStep("analysis", runtime, ADKRunRequest(workflow_id, "c7", "analyst", {"_system_prompt": ANALYST_INSTRUCTION, "task": "Analyze prior setup"})),
        SequentialWorkflowStep("decision", runtime, ADKRunRequest(workflow_id, "c7", "governor", {"_system_prompt": GOVERNOR_INSTRUCTION, "task": "Final verdict"}))
    )
    
    print("  Running Business System: Research -> Analysis -> Approval")
    results = workflow.run(steps=steps)
    
    for res in results:
        role = res.agent_name.replace("_", " ").title()
        text = _extract_text(res.output_payload)
        print(f"\n  [ {role} ]")
        print(f"    {text[:200]}...")

    print("\n  Multi-agent business system execution complete.")

# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "#"*78)
    print("#  Multi-Agent Systems — Advanced Orchestration Examples")
    print("#"*78)

    examples = [
        example_01_multi_agent_architecture,
        example_02_orchestration,
        example_03_routing_data_flow,
        example_04_state_management,
        example_05_orchestration_state_coordination,
        example_06_multi_agent_rag,
        example_07_complete_business_system,
    ]

    for ex in examples:
        try:
            ex()
        except Exception as e:
            print(f"\n  ERROR in {ex.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "#"*78)
    print("#  All multi-agent examples complete!")
    print("#"*78 + "\n")

if __name__ == "__main__":
    main()
