"""Agentic Workflows — Platform Usage Examples (All 6 Phases).

Demonstrates the 6 core agentic workflow patterns and 6 platform phases:
  Patterns:
    1. Agentic Workflow Modeling (Contracts & Steps)
    2. Agentic Prompt Chaining (Contextual pipelines)
    3. Agentic Routing (Dynamic path selection)
    4. Agentic Parallelization (Fan-out/Fan-in)
    5. Agentic Evaluator-Optimizer (Refinement loops)
    6. Agentic Orchestrator-Workers (Delegated execution)

  Platform Phases:
    Phase 1: Foundation (MT5, SQL, Tool Validation, Pricing)
    Phase 2: Tool Calling (Executor)
    Phase 3: RAG System (Retrieval, Reformulation)
    Phase 4: Long-term Memory (Semantic, Episodic, Procedural)
    Phase 5: Evaluation (Trajectory, Benchmarks)
    Phase 6: Production (Streaming, OTel, LLM Compression)

Usage:
    python backend/scripts/examples/agentic_ai/02_agentic_workflows.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union
from uuid import uuid4

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

def _load_example_env() -> None:
    """Load example environment defaults."""
    env_path = Path(PROJECT_ROOT) / "backend" / "config" / "environments" / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_example_env()

# Suppress noise
warnings.filterwarnings("ignore", message=r"authlib\.jose module is deprecated")
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\] feature FeatureName\.PLUGGABLE_AUTH")

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.agents.runtime import (
    LLMRuntime,
    create_llm_runtime,
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    ADKRunResult,
    AgentExecutionContext,
    PromptComposingMiddleware,
)
from backend.agents.runtime.workflows import (
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
    RoutingWorkflowRunner,
    RoutingWorkflowBranch,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
    EvaluatorOptimizerWorkflowRunner,
    EvaluatorOptimizerStep,
    OrchestratorWorkerWorkflowRunner,
    OrchestratorWorkerTask,
)
from backend.agents.runtime.evaluator import TrajectoryEvaluation, EvaluatorRubric
from backend.agents.runtime.output_validation import CanonicalOutputValidator

# ── Phase 1-6 Imports (Foundational Infrastructure) ──────────────────
from backend.mcp.mt5_mcp.server import create_legacy_mt5_mcp_server, create_mt5_mcp_server
from backend.mcp.sql_mcp.tools import SQLReadOnlyTools, SQLMCPAccessError
from backend.agents.runtime import ToolValidator, ToolValidationError
from backend.agents.runtime.tool_validation import register_mcp_schemas
from backend.observability.cost_tracker import CostTracker, MODEL_PRICING, calculate_cost
from backend.agents.runtime import ToolCall, ToolResult, ToolExecutor
from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.ingestion import DocumentIngester
from backend.retrieval.service import RetrievalService
from backend.retrieval.reformulation import RetrievalReformulator
from backend.retrieval.evaluation import RetrievalEvaluator
from backend.agents.memory.semantic import SemanticMemoryStore
from backend.agents.memory.episodic import EpisodicMemoryStore
from backend.agents.memory.procedural import ProceduralMemoryStore
from backend.agents.memory.rules import MemoryWriteRules
from backend.agents.runtime.workflow_log import WorkflowLogCollector
from tests.eval.trajectory_eval import TrajectoryEvaluator
from backend.agents.runtime.streaming import run_streaming
from backend.observability.otel_exporter import OpenTelemetryExporter
from backend.orchestration.context_engineering.llm_compression import LLMContextCompressor

# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def print_example_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)

def print_section(label: str, value: Any) -> None:
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    print(f"  {label:<35s} {value}")

def print_json(title: str, payload: dict[str, Any]) -> None:
    print(f"  {title}:")
    print("    " + json.dumps(payload, indent=2, default=str).replace("\n", "\n    "))

def _default_model_name() -> str:
    from backend.config.agent_model import AGENT_MODEL
    return os.environ.get("HARUQUANT_AGENT_MODEL", AGENT_MODEL)

def _get_live_runner() -> tuple[ADKRunnerService, LLMRuntime]:
    model = _default_model_name()
    runtime = create_llm_runtime(model=model, temperature=0.1, json_mode=False)
    runner = ADKRunnerService(config=ADKRunnerConfig(runner_name="workflow_demo", default_model=model))
    return runner, runtime

def _extract_text(payload: dict[str, Any]) -> str:
    if "content" in payload: return str(payload["content"])
    if "_raw_text" in payload: return str(payload["_raw_text"])
    if len(payload) == 1: return str(list(payload.values())[0])
    return json.dumps(payload)

# ────────────────────────────────────────────────────────────────────────
# 1. Agentic Workflow Modeling
# ────────────────────────────────────────────────────────────────────────

def example_01_workflow_modeling() -> None:
    """Modeling: steps, contracts, and validation requirements."""
    print_example_header("01: Agentic Workflow Modeling")
    
    runner, runtime = _get_live_runner()
    
    # Define a model for a strategy research step
    step = SequentialWorkflowStep(
        step_name="market_research",
        runtime_agent=runtime,
        request=ADKRunRequest(
            workflow_id="modeling-wf",
            correlation_id="corr-1",
            agent_name="research_agent",
            input_payload={"symbol": "EURUSD", "instruction": "Analyze H1 trend."}
        ),
        input_contract_type="ResearchRequest",
        expected_output_contract_type="ResearchReport",
        validate_before_next=True
    )
    
    print_section("Step name:", step.step_name)
    print_section("Agent name:", step.request.agent_name)
    print_section("Expected contract:", step.expected_output_contract_type)
    print_section("Validation enabled:", step.validate_before_next)

# ────────────────────────────────────────────────────────────────────────
# 2. Agentic Prompt Chaining Workflows
# ────────────────────────────────────────────────────────────────────────

def example_02_prompt_chaining() -> None:
    """Prompt Chaining: sequential execution where context flows between steps."""
    print_example_header("02: Agentic Prompt Chaining Workflows")
    
    runner, runtime = _get_live_runner()
    workflow = SequentialWorkflowRunner(runner)
    
    steps = (
        SequentialWorkflowStep(
            step_name="fetch_regime",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="chain-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="regime_agent",
                input_payload={"task": "Determine if EURUSD H1 is trending or ranging. Output 1 sentence."}
            )
        ),
        SequentialWorkflowStep(
            step_name="generate_strategy",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="chain-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="strategy_agent",
                input_payload={"task": "Based on the regime, suggest a trade idea. Output 1 sentence."}
            )
        )
    )
    
    print("  Executing 2-step prompt chain...")
    results = workflow.run(steps=steps)
    
    for i, res in enumerate(results):
        text = _extract_text(res.output_payload)
        print_section(f"Step {i+1} ({res.agent_name}) output:", text[:100] + "...")

# ────────────────────────────────────────────────────────────────────────
# 3. Agentic Routing Workflows
# ────────────────────────────────────────────────────────────────────────

def example_03_routing_workflow() -> None:
    """Routing: dynamic path selection based on an initial decision."""
    print_example_header("03: Agentic Routing Workflows")
    
    runner, runtime = _get_live_runner()
    
    # Decision: Should we execute a trade or keep researching?
    decision_task = "User wants to buy EURUSD but volatility is high. Decision: RESEARCH or EXECUTE?"
    
    # In a real scenario, a router agent would produce the route_key.
    # Here we show the runner executing the selected branch.
    routing_runner = RoutingWorkflowRunner(runner)
    
    branches = (
        RoutingWorkflowBranch(
            route_key="RESEARCH",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="route-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="research_agent",
                input_payload={"task": "Perform deep risk analysis."}
            )
        ),
        RoutingWorkflowBranch(
            route_key="EXECUTE",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="route-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="execution_agent",
                input_payload={"task": "Place market order."}
            )
        )
    )
    
    print_section("Decision Logic:", decision_task)
    print_section("Selected Route:", "RESEARCH")
    
    result = routing_runner.run(route_key="RESEARCH", branches=branches)
    text = _extract_text(result.output_payload)
    print_section("Branch Agent:", result.agent_name)
    print_section("Output:", text[:60] + "...")

# ────────────────────────────────────────────────────────────────────────
# 4. Agentic Parallelization Workflows
# ────────────────────────────────────────────────────────────────────────

def example_04_parallelization() -> None:
    """Parallelization: concurrent analysis of multiple assets (fan-out/fan-in)."""
    print_example_header("04: Agentic Parallelization Workflows")
    
    runner, runtime = _get_live_runner()
    parallel_runner = ParallelWorkflowRunner(runner)
    
    tasks = (
        ParallelWorkflowTask(
            task_name="eurusd_analysis",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="para-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="analyst_1",
                input_payload={"task": "Analyze EURUSD. Output: BULLISH or BEARISH."}
            )
        ),
        ParallelWorkflowTask(
            task_name="gbpusd_analysis",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="para-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="analyst_2",
                input_payload={"task": "Analyze GBPUSD. Output: BULLISH or BEARISH."}
            )
        )
    )
    
    print("  Executing parallel tasks (Fan-out)...")
    aggregate = parallel_runner.run(tasks=tasks)
    
    print_section("Successful tasks:", aggregate.successful_tasks)
    for name, res in aggregate.results.items():
        text = _extract_text(res.output_payload)
        print_section(f"  {name} output:", text.strip())

# ────────────────────────────────────────────────────────────────────────
# 5. Agentic Evaluator-Optimizer Workflows
# ────────────────────────────────────────────────────────────────────────

def example_05_evaluator_optimizer() -> None:
    """Evaluator-Optimizer: iterative refinement loop with quality feedback."""
    print_example_header("05: Agentic Evaluator-Optimizer Workflows")
    
    runner, runtime = _get_live_runner()
    optimizer = EvaluatorOptimizerWorkflowRunner(runner)
    
    # A simple evaluator that checks for "confidence" in the text
    def simple_evaluator(res: ADKRunResult) -> float:
        text = _extract_text(res.output_payload).lower()
        if "confidence" in text or "evidence" in text:
            return 1.0
        return 0.5

    generator_step = EvaluatorOptimizerStep(
        runtime_agent=runtime,
        request=ADKRunRequest(
            workflow_id="eval-wf",
            correlation_id=uuid4().hex[:8],
            agent_name="writer_agent",
            input_payload={"task": "Draft a trade hypothesis for EURUSD."}
        )
    )
    
    print("  Starting refinement loop (max 2 iterations)...")
    result = optimizer.run(
        generator_step=generator_step,
        evaluator=simple_evaluator,
        acceptance_threshold=0.9,
        max_iterations=2
    )
    
    print_section("Total iterations:", result.iterations)
    print_section("Final verdict:", result.terminated_by)
    print_section("Scores:", result.evaluation_scores)
    text = _extract_text(result.final_result.output_payload)
    print_section("Final content:", text[:100] + "...")

# ────────────────────────────────────────────────────────────────────────
# 8. Complete Multi-Agent Project Management
# ────────────────────────────────────────────────────────────────────────

def example_08_complete() -> None:
    """Complete: Library of specialized agents managing a technical project."""
    print_example_header("08: Complete Multi-Agent Workflow (Project Management)")

    runner, runtime = _get_live_runner()
    
    # 1. Define our 'Agent Library' via specialized instructions
    class AgentRoles:
        PM = (
            "You are a Project Manager. Define clear, actionable requirements "
            "and milestones for the project. Focus on scope and value."
        )
        ARCHITECT = (
            "You are a Technical Architect. Design a high-level system architecture "
            "based on requirements. Focus on scalability, security, and components."
        )
        DEVELOPER = (
            "You are a Senior Developer. Create a detailed implementation plan. "
            "Focus on specific technologies, API endpoints, and data structures."
        )

    project_task = "Implement a high-performance WebSocket gateway for real-time trade alerts."
    workflow_id = f"project-{uuid4().hex[:4]}"
    
    # 2. Build the Multi-Step Workflow
    workflow = SequentialWorkflowRunner(runner)
    
    steps = (
        SequentialWorkflowStep(
            step_name="requirements",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id=workflow_id,
                correlation_id=uuid4().hex[:8],
                agent_name="project_manager",
                input_payload={
                    "_system_prompt": AgentRoles.PM,
                    "task": f"Define requirements for: {project_task}"
                }
            )
        ),
        SequentialWorkflowStep(
            step_name="architecture",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id=workflow_id,
                correlation_id=uuid4().hex[:8],
                agent_name="architect",
                input_payload={
                    "_system_prompt": AgentRoles.ARCHITECT,
                    "task": "Design the architecture based on the requirements provided in context."
                }
            )
        ),
        SequentialWorkflowStep(
            step_name="implementation",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id=workflow_id,
                correlation_id=uuid4().hex[:8],
                agent_name="developer",
                input_payload={
                    "_system_prompt": AgentRoles.DEVELOPER,
                    "task": "Draft the implementation plan based on the architecture in context."
                }
            )
        )
    )

    print(f"  Managing Project: {project_task}")
    print("  Orchestrating PM -> Architect -> Developer...")
    
    results = workflow.run(steps=steps)

    for res in results:
        role = res.agent_name.replace("_", " ").title()
        text = _extract_text(res.output_payload)
        print(f"\n  [ {role} ]")
        for line in text.splitlines()[:5]: # Show first 5 lines
            print(f"    {line}")
        if len(text.splitlines()) > 5:
            print("    ...")

    print("\n  Multi-agent project management workflow complete.")


# ────────────────────────────────────────────────────────────────────────
# 6. Agentic Orchestrator-Workers
# ────────────────────────────────────────────────────────────────────────

def example_06_orchestrator_workers() -> None:
    """Orchestrator-Workers: complex plan synthesis and delegation."""
    print_example_header("06: Agentic Orchestrator-Workers")
    
    runner, runtime = _get_live_runner()
    
    # 1. Orchestrator defines a plan
    plan = {
        "tasks": [
            {"worker": "research", "task": "Fetch market sentiment."},
            {"worker": "compliance", "task": "Check regulatory limits."}
        ]
    }
    
    # 2. Runner dispatches to specialized workers
    orchestrator_runner = OrchestratorWorkerWorkflowRunner(runner)
    
    tasks = (
        OrchestratorWorkerTask(
            worker_name="researcher",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="orch-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="research_agent",
                input_payload={"task": plan["tasks"][0]["task"]}
            )
        ),
        OrchestratorWorkerTask(
            worker_name="compliance",
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="orch-wf",
                correlation_id=uuid4().hex[:8],
                agent_name="compliance_agent",
                input_payload={"task": plan["tasks"][1]["task"]}
            )
        )
    )
    
    print("  Orchestrator dispatching tasks to workers...")
    group_result = orchestrator_runner.run(tasks=tasks)
    
    print_section("Workers completed:", list(group_result.results.keys()))
    print_section("Synthesized keys:", list(group_result.synthesized_output.keys()))

# ────────────────────────────────────────────────────────────────────────
# Platform Infrastructure (Phases 1-6 Foundations)
# ────────────────────────────────────────────────────────────────────────

def example_07_platform_foundation() -> None:
    """Selected platform infrastructure highlights (Phases 1-6)."""
    print_example_header("07: Platform Infrastructure Foundations")
    
    # Phase 1.6: Model Pricing
    print_section("Registered pricing models:", len(MODEL_PRICING))
    cost = calculate_cost("gemini-3.1-flash-lite-preview", 1000, 500)
    print_section("Gemini 1K in/0.5K out cost:", f"${cost:.6f}")
    
    # Phase 1.3: Tool Validation
    validator = ToolValidator()
    register_mcp_schemas(validator)
    print_section("Tool validation:", "Operational (MT5 schemas registered)")

    # Phase 4.1: Memory Rules
    should_remember = MemoryWriteRules.should_remember_semantic("Important EURUSD signal", 0.9)
    print_section("Memory write logic:", f"High importance should remember: {should_remember}")

    # Phase 6.2: Context Compression
    compressor = LLMContextCompressor(llm_runtime=None)
    compressed = compressor.compress([{"content": "A" * 1000}, {"content": "B" * 1000}], target_tokens=10)
    print_section("Context Compression:", f"2000 chars -> {len(compressed)} chars")

# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("#" * 78)
    print("#  Agentic Workflows — Platform Usage Examples")
    print("#  Logical Incremental Order: Patterns -> Infrastructure")
    print("#" * 78)

    examples = [
        example_01_workflow_modeling,
        example_02_prompt_chaining,
        example_03_routing_workflow,
        example_04_parallelization,
        example_05_evaluator_optimizer,
        example_06_orchestrator_workers,
        example_08_complete,
        example_07_platform_foundation,
    ]

    for example_fn in examples:
        try:
            example_fn()
        except Exception as exc:
            print(f"\n  ERROR in {example_fn.__name__}: {exc}")
            import traceback
            traceback.print_exc()

    print()
    print("#" * 78)
    print("#  All agentic workflow examples complete!")
    print("#" * 78)
    print()

if __name__ == "__main__":
    main()
