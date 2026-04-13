"""Agentic Workflows — Usage Examples

Demonstrates all workflow patterns and agentic orchestration capabilities:
  1. Sequential Workflow (linear pipeline with context chaining)
  2. Routing Workflow (intent-based dispatch)
  3. Parallel Workflow (fan-out / fan-in)
  4. Evaluator-Optimizer Loop (generate → evaluate → refine)
  5. Orchestrator-Workers (dynamic task graph)
  6. Approval-Aware Workflow (human-in-the-loop gates)
  7. Compensation-Aware Workflow (rollback on partial failure)
  8. Escalation-Aware Workflow (policy & ambiguity triggers)
  9. Context Engineering (budget, eviction, compression)
  10. Cost Governance (per-workflow budget tracking)

Usage:
    python backend/scripts/examples/agentic_ai/02_agentic_workflows.py
"""

import json
import os
import sys
import time
from dataclasses import replace
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from backend.common.logger import logger

# ── Workflow runners ────────────────────────────────────────────────────
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
    RefineLoopGuardDecision,
    enforce_refine_loop_limit,
)
from backend.agents.runtime.runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerService,
    ADKRunnerConfig,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentRuntime,
)

# ── Prompt composition ──────────────────────────────────────────────────
from backend.agents.prompts import PromptComposer, PromptContext

# ── Context engineering ─────────────────────────────────────────────────
from backend.orchestration.context_engineering import (
    ContextBudget,
    ContextEviction,
    ContextCompression,
    ContextValidator,
    ContradictionResolver,
)

# ── Cost governance ─────────────────────────────────────────────────────
from backend.services.cost import CostEnforcer, cost_enforcer

# ── Approval system ─────────────────────────────────────────────────────
from backend.services.approval import ApprovalPacket, ApprovalRequest, ApprovalState, RiskClass


# ────────────────────────────────────────────────────────────────────────
# Mock agent runtime for examples (no real LLM needed for demos)
# ────────────────────────────────────────────────────────────────────────

class MockAgentRuntime:
    """Mock agent that returns predefined payloads — no LLM required."""

    def __init__(self, responses: Optional[List[dict]] = None) -> None:
        self._responses = responses or []
        self._call_index = 0
        self.calls: List[dict] = []

    def run(self, *, request: ADKRunRequest, context: AgentExecutionContext) -> AgentExecutionResult:
        self.calls.append({
            "agent_name": request.agent_name,
            "input_payload": dict(request.input_payload),
            "context_model": context.model,
        })

        if self._responses and self._call_index < len(self._responses):
            payload = self._responses[self._call_index]
            self._call_index += 1
        else:
            payload = {"status": "ok", "agent": request.agent_name}

        return AgentExecutionResult(
            output_payload=payload,
            final_state="COMPLETED",
            tool_calls=(),
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────

def print_example_header(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def print_section(label: str, value: str) -> None:
    print(f"  {label:<25s} {value}")


def print_json(title: str, data: dict, indent: int = 4) -> None:
    print(f"{' ' * indent}{title}:")
    print("  " + json.dumps(data, indent=2).replace("\n", "\n  "))


def _make_runner(responses: Optional[List[dict]] = None) -> ADKRunnerService:
    """Create an ADKRunnerService backed by a MockAgentRuntime."""
    return ADKRunnerService(ADKRunnerConfig(runner_name="demo"))


def _make_request(agent_name: str, payload: dict) -> tuple[ADKRunRequest, AgentExecutionContext]:
    request = ADKRunRequest(
        workflow_id="demo-wf",
        correlation_id="demo-corr",
        agent_name=agent_name,
        input_payload=payload,
    )
    context = AgentExecutionContext(
        workflow_id="demo-wf",
        correlation_id="demo-corr",
        session_id=None,
        model="demo-model",
        allowed_tools=(),
        prompt_version_id=None,
        metadata={},
    )
    return request, context


class MockWorkflowAgent:
    """Wraps a MockAgentRuntime to conform to AgentRuntime protocol."""

    def __init__(self, name: str, responses: Optional[List[dict]] = None) -> None:
        self._mock = MockAgentRuntime(responses)
        self._name = name
        self.calls: List[dict] = []

    def run(self, *, request: ADKRunRequest, context: AgentExecutionContext) -> AgentExecutionResult:
        self.calls.append({"agent": self._name, "input": dict(request.input_payload)})
        return self._mock.run(request=request, context=context)


# ────────────────────────────────────────────────────────────────────────
# Example 01: Sequential Workflow
# ────────────────────────────────────────────────────────────────────────

def example_01_sequential_workflow() -> None:
    """Demonstrate a linear pipeline: data fetch → analysis → report."""
    print_example_header("Example 01: Sequential Workflow")

    runner = SequentialWorkflowRunner(_make_runner())

    steps = (
        SequentialWorkflowStep(
            step_name="fetch_market_data",
            runtime_agent=MockWorkflowAgent("data_agent", [{"status": "fetched", "bars": 200}]),
            request=ADKRunRequest(
                workflow_id="wf-001",
                correlation_id="corr-001",
                agent_name="data_agent",
                input_payload={"symbol": "EURUSD", "timeframe": "H1"},
            ),
        ),
        SequentialWorkflowStep(
            step_name="analyze_regime",
            runtime_agent=MockWorkflowAgent("regime_agent", [{"regime": "trending", "confidence": 0.82}]),
            request=ADKRunRequest(
                workflow_id="wf-001",
                correlation_id="corr-001",
                agent_name="regime_agent",
                input_payload={"symbol": "EURUSD"},
            ),
        ),
        SequentialWorkflowStep(
            step_name="generate_hypothesis",
            runtime_agent=MockWorkflowAgent("strategy_agent", [
                {"direction": "long", "confidence": 0.74, "entry": 1.0875}
            ]),
            request=ADKRunRequest(
                workflow_id="wf-001",
                correlation_id="corr-001",
                agent_name="strategy_agent",
                input_payload={"symbol": "EURUSD", "timeframe": "H1"},
            ),
        ),
    )

    results = runner.run(steps=steps)

    print_section("Steps executed:", f"{len(results)}")
    for i, result in enumerate(results, 1):
        print_section(f"  Step {i} output:", json.dumps(result.output_payload))

    print_section("Pattern:", "Sequential — each step runs after the previous completes")


# ────────────────────────────────────────────────────────────────────────
# Example 02: Routing Workflow
# ────────────────────────────────────────────────────────────────────────

def example_02_routing_workflow() -> None:
    """Demonstrate intent-based dispatch to specialist agents."""
    print_example_header("Example 02: Routing Workflow (Intent-Based Dispatch)")

    runner = RoutingWorkflowRunner(_make_runner())

    branches = (
        RoutingWorkflowBranch(
            route_key="market_data",
            runtime_agent=MockWorkflowAgent("data_agent", [{"data": "OHLCV bars fetched"}]),
            request=ADKRunRequest(
                workflow_id="wf-002",
                correlation_id="corr-002",
                agent_name="data_agent",
                input_payload={"intent": "market_data"},
            ),
        ),
        RoutingWorkflowBranch(
            route_key="risk_analysis",
            runtime_agent=MockWorkflowAgent("risk_agent", [{"var": 0.05, "es": 0.07}]),
            request=ADKRunRequest(
                workflow_id="wf-002",
                correlation_id="corr-002",
                agent_name="risk_agent",
                input_payload={"intent": "risk_analysis"},
            ),
        ),
        RoutingWorkflowBranch(
            route_key="trade_hypothesis",
            runtime_agent=MockWorkflowAgent("strategy_agent", [{"direction": "long"}]),
            request=ADKRunRequest(
                workflow_id="wf-002",
                correlation_id="corr-002",
                agent_name="strategy_agent",
                input_payload={"intent": "trade_hypothesis"},
            ),
        ),
    )

    # Route to risk_analysis
    result = runner.run(route_key="risk_analysis", branches=branches)
    print_section("Route key:", "risk_analysis")
    print_section("Dispatched to:", result.output_payload)
    print_section("Pattern:", "Routing — one branch selected by intent classification")


# ────────────────────────────────────────────────────────────────────────
# Example 03: Parallel Workflow
# ────────────────────────────────────────────────────────────────────────

def example_03_parallel_workflow() -> None:
    """Demonstrate fan-out / fan-in: independent tasks run concurrently."""
    print_example_header("Example 03: Parallel Workflow (Fan-Out / Fan-In)")

    runner = ParallelWorkflowRunner(_make_runner())

    tasks = (
        ParallelWorkflowTask(
            task_name="volatility_analysis",
            runtime_agent=MockWorkflowAgent("volatility_agent", [{"atr": 0.0025, "regime": "normal"}]),
            request=ADKRunRequest(
                workflow_id="wf-003",
                correlation_id="corr-003",
                agent_name="volatility_agent",
                input_payload={"symbol": "EURUSD"},
            ),
        ),
        ParallelWorkflowTask(
            task_name="correlation_check",
            runtime_agent=MockWorkflowAgent("correlation_agent", [{"avg_corr": 0.35, "cluster_risk": "low"}]),
            request=ADKRunRequest(
                workflow_id="wf-003",
                correlation_id="corr-003",
                agent_name="correlation_agent",
                input_payload={"symbols": ["EURUSD", "GBPUSD", "AUDUSD"]},
            ),
        ),
        ParallelWorkflowTask(
            task_name="regime_detection",
            runtime_agent=MockWorkflowAgent("regime_agent", [{"regime": "trending", "confidence": 0.82}]),
            request=ADKRunRequest(
                workflow_id="wf-003",
                correlation_id="corr-003",
                agent_name="regime_agent",
                input_payload={"symbol": "EURUSD"},
            ),
        ),
    )

    results = runner.run(tasks=tasks)

    print_section("Tasks dispatched:", f"{len(results)} (fan-out)")
    for task_name, result in results.items():
        print_section(f"  {task_name}:", json.dumps(result.output_payload))
    print_section("Pattern:", "Parallel — independent tasks, fan-in to keyed result map")


# ────────────────────────────────────────────────────────────────────────
# Example 04: Evaluator-Optimizer Loop
# ────────────────────────────────────────────────────────────────────────

def example_04_evaluator_optimizer() -> None:
    """Demonstrate generate → evaluate → refine until acceptance threshold."""
    print_example_header("Example 04: Evaluator-Optimizer Loop")

    runner = EvaluatorOptimizerWorkflowRunner(_make_runner())

    # Simulated evaluator: scores increase each iteration
    iteration_scores = [0.45, 0.62, 0.78, 0.88]
    score_index = [0]

    def evaluator(result: ADKRunResult) -> float:
        score = iteration_scores[min(score_index[0], len(iteration_scores) - 1)]
        score_index[0] += 1
        return score

    gen_step = EvaluatorOptimizerStep(
        runtime_agent=MockWorkflowAgent("generator", [
            {"draft": "v1", "quality": "poor"},
            {"draft": "v2", "quality": "improving"},
            {"draft": "v3", "quality": "good"},
            {"draft": "v4", "quality": "excellent"},
        ]),
        request=ADKRunRequest(
            workflow_id="wf-004",
            correlation_id="corr-004",
            agent_name="generator",
            input_payload={"goal": "Generate trade hypothesis"},
        ),
    )

    result = runner.run(
        generator_step=gen_step,
        evaluator=evaluator,
        acceptance_threshold=0.85,
        max_iterations=5,
    )

    print_section("Final result:", json.dumps(result.final_result.output_payload))
    print_section("Scores:", f"[{', '.join(f'{s:.2f}' for s in result.evaluation_scores)}]")
    print_section("Iterations:", f"{result.iterations}")
    print_section("Terminated by:", result.terminated_by)
    print_section("Pattern:", "Evaluator-Optimizer — loop until score >= threshold or max iterations")


# ────────────────────────────────────────────────────────────────────────
# Example 05: Orchestrator-Workers
# ────────────────────────────────────────────────────────────────────────

def example_05_orchestrator_workers() -> None:
    """Demonstrate dynamic task graph: orchestrator plans, workers execute."""
    print_example_header("Example 05: Orchestrator-Workers")

    runner = OrchestratorWorkerWorkflowRunner(_make_runner())

    tasks = (
        OrchestratorWorkerTask(
            worker_name="market_data_worker",
            runtime_agent=MockWorkflowAgent("data_agent", [{"bars": 200, "symbol": "EURUSD"}]),
            request=ADKRunRequest(
                workflow_id="wf-005",
                correlation_id="corr-005",
                agent_name="data_agent",
                input_payload={"task": "fetch_data"},
            ),
        ),
        OrchestratorWorkerTask(
            worker_name="risk_check_worker",
            runtime_agent=MockWorkflowAgent("risk_agent", [{"var_ok": True, "margin_ok": True}]),
            request=ADKRunRequest(
                workflow_id="wf-005",
                correlation_id="corr-005",
                agent_name="risk_agent",
                input_payload={"task": "check_limits"},
            ),
        ),
        OrchestratorWorkerTask(
            worker_name="signal_worker",
            runtime_agent=MockWorkflowAgent("strategy_agent", [{"signal": "bullish", "confidence": 0.74}]),
            request=ADKRunRequest(
                workflow_id="wf-005",
                correlation_id="corr-005",
                agent_name="strategy_agent",
                input_payload={"task": "generate_signal"},
            ),
        ),
    )

    results = runner.run(tasks=tasks)

    print_section("Workers dispatched:", f"{len(results)}")
    for worker_name, result in results.items():
        print_section(f"  {worker_name}:", json.dumps(result.output_payload))
    print_section("Pattern:", "Orchestrator-Workers — dynamic task graph dispatched to specialists")


# ────────────────────────────────────────────────────────────────────────
# Example 06: Approval-Aware Workflow
# ────────────────────────────────────────────────────────────────────────

def example_06_approval_aware_workflow() -> None:
    """Demonstrate human-in-the-loop approval gate before execution."""
    print_example_header("Example 06: Approval-Aware Workflow")

    # Build an approval packet per Playbook §11.2
    packet = ApprovalPacket(
        action="place_order",
        reason="Signal confirmed by strategy and risk checks",
        evidence=[
            {"source": "strategy", "signal": "bullish", "confidence": 0.74},
            {"source": "risk_check", "var_ok": True, "margin_ok": True},
        ],
        confidence=0.74,
        uncertainty={"market_regime": "may shift on ECB news"},
        policy_checks_passed=["var_check", "margin_check", "concentration_check"],
        risk_class=RiskClass.C,
        alternatives_considered=["reduce_size", "defer_trade"],
        expected_impact={"financial": "+$150 expected", "risk": "low"},
        rollback_plan="close_position_if_post_check_fails",
        escalation_triggers=["policy_conflict", "missing_evidence"],
    )

    request = ApprovalRequest(
        approval_id="appr-001",
        action_type="place_order",
        target_ref_type="trade_hypothesis",
        target_ref_id="hyp-001",
        required_count=1,
        state=ApprovalState.PENDING,
        created_by_actor_type="agent",
        created_by_actor_id="strategy_agent",
        packet=packet,
    )

    print_section("Approval packet validation:", "✓" if packet.is_complete() else "✗ incomplete")
    print_section("Risk class:", request.packet.risk_class.value)
    print_section("Evidence count:", str(len(request.packet.evidence)))
    print_section("Alternatives:", str(len(request.packet.alternatives_considered)))
    print_section("Rollback plan:", request.packet.rollback_plan[:40] + "...")
    print_section("Approval state:", request.state)
    print_section("Pattern:", "Approval-Aware — full packet with evidence, rollback, escalation triggers")


# ────────────────────────────────────────────────────────────────────────
# Example 07: Compensation-Aware Workflow
# ────────────────────────────────────────────────────────────────────────

def example_07_compensation_aware_workflow() -> None:
    """Demonstrate compensation plans for partial failure rollback."""
    print_example_header("Example 07: Compensation-Aware Workflow")

    from backend.services.execution.compensation import (
        CompensationRegistry,
        OrderCompensationPlan,
        PositionCompensationPlan,
    )

    registry = CompensationRegistry()

    # Simulate a workflow that partially fails
    workflow_steps = [
        {"step": "fetch_data", "status": "ok"},
        {"step": "analyze_regime", "status": "ok"},
        {"step": "place_order", "status": "failed", "error": "spread_too_wide"},
    ]

    print("  Workflow execution:")
    for step in workflow_steps:
        icon = "✓" if step["status"] == "ok" else "✗"
        print(f"    {icon} {step['step']}: {step['status']}")
        if step["status"] == "failed":
            # Get compensation plan for this action class
            plan = registry.get_plan("C", f"comp_{step['step']}")
            if plan and plan.validate({"order_type": "entry"}):
                success = plan.execute({"order_type": "entry"})
                print(f"      → Compensation executed: {'success' if success else 'failed'}")
                print(f"      → Log entries: {len(plan.log_entries)}")
                for entry in plan.log_entries:
                    print(f"        {entry}")

    print_section("Pattern:", "Compensation-Aware — on failure, execute compensating action")


# ────────────────────────────────────────────────────────────────────────
# Example 08: Escalation-Aware Workflow
# ────────────────────────────────────────────────────────────────────────

def example_08_escalation_aware_workflow() -> None:
    """Demonstrate escalation triggers and RefineLoopGuard."""
    print_example_header("Example 08: Escalation-Aware Workflow")

    # Simulate escalation triggers
    escalation_scenarios = [
        {"trigger": "policy_conflict", "action": "ESCALATE", "reason": "VaR exceeds limit"},
        {"trigger": "missing_evidence", "action": "ESCALATE", "reason": "No market data available"},
        {"trigger": "repeated_failure", "action": "ESCALATE", "reason": "3 consecutive failures"},
        {"trigger": "none", "action": "PROCEED", "reason": "All checks passed"},
    ]

    print("  Escalation decision matrix:")
    for scenario in escalation_scenarios:
        icon = "⚠" if scenario["action"] == "ESCALATE" else "✓"
        print(f"    {icon} trigger={scenario['trigger']:<20s} → {scenario['action']} ({scenario['reason']})")

    # RefineLoopGuard
    max_iterations = 3
    for iteration in range(5):
        decision = enforce_refine_loop_limit(iteration_count=iteration, max_iterations=max_iterations)
        icon = "✓" if decision.allowed else "⛔"
        print(f"    {icon} Iteration {iteration}: {'allowed' if decision.allowed else 'BLOCKED'}")
        if decision.reason_codes:
            print(f"       reason: {', '.join(decision.reason_codes)}")

    print_section("Pattern:", "Escalation-Aware — explicit triggers + loop iteration guards")


# ────────────────────────────────────────────────────────────────────────
# Example 09: Context Engineering
# ────────────────────────────────────────────────────────────────────────

def example_09_context_engineering() -> None:
    """Demonstrate context budget, eviction, compression, and validation."""
    print_example_header("Example 09: Context Engineering")

    # Context budget
    budget = ContextBudget(max_tokens=4096, reserved_tokens=512, per_step_budget=1024)
    budget.allocate(800)
    budget.allocate(600)
    print_section("Context budget:", f"{budget.used}/{budget.max_tokens} used, {budget.available} available")

    # Context eviction
    eviction = ContextEviction(ttl_seconds=300, max_entries=5)
    for i in range(7):
        eviction.put(f"key_{i}", f"value_{i}")
    print_section("Context eviction:", f"{eviction.size} entries (max 5, evicted overflow)")

    # Context compression
    compressor = ContextCompression(max_items=5, abstraction_levels=3)
    items = [{"bar": i, "close": 1.0800 + i * 0.0001} for i in range(20)]
    compressed = compressor.compress(items)
    ratio = compressor.estimate_compression_ratio(items)
    print_section("Context compression:", f"{len(items)} → {len(compressed)} items (ratio: {ratio:.2f})")

    # Context validation
    validator = ContextValidator()
    valid_ctx = {"data": "fresh market data", "_timestamp": time.time(), "_source_trust_level": 2}
    invalid_ctx = {}
    print_section("Context validation:", f"valid={len(validator.validate(valid_ctx)) == 0}, invalid={len(validator.validate(invalid_ctx)) > 0}")

    # Contradiction detection
    resolver = ContradictionResolver()
    sources = [
        {"source_type": "tool_A", "data": {"price": 1.0850}},
        {"source_type": "tool_B", "data": {"price": 1.0855}},
    ]
    contradictions = resolver.detect(sources)
    print_section("Contradiction detection:", f"{len(contradictions)} found")

    print_section("Pattern:", "Context Engineering — budget, eviction, compression, validation, contradiction resolution")


# ────────────────────────────────────────────────────────────────────────
# Example 10: Cost Governance
# ────────────────────────────────────────────────────────────────────────

def example_10_cost_governance() -> None:
    """Demonstrate cost tracking and budget enforcement per workflow."""
    print_example_header("Example 10: Cost Governance")

    enforcer = CostEnforcer()

    # Simulate a workflow with multiple LLM calls
    workflow_costs = [
        {"step": "market_data_fetch", "tokens_in": 120, "tokens_out": 50},
        {"step": "regime_detection", "tokens_in": 200, "tokens_out": 80},
        {"step": "hypothesis_generation", "tokens_in": 300, "tokens_out": 150},
        {"step": "risk_check", "tokens_in": 150, "tokens_out": 60},
    ]

    total_cost = 0.0
    print("  Workflow cost tracking:")
    for step in workflow_costs:
        enforcer.record_cost(
            trace_id="wf-cost-001",
            span_id=step["step"],
            model="gemini-3.1-flash-lite-preview",
            input_tokens=step["tokens_in"],
            output_tokens=step["tokens_out"],
        )
        step_cost = step["tokens_in"] * 0.000001 + step["tokens_out"] * 0.000003
        total_cost += step_cost
        print(f"    {step['step']}: {step['tokens_in']}in/{step['tokens_out']}out → ${step_cost:.4f}")

    print_section("Total workflow cost:", f"${total_cost:.4f}")
    budget_ok = enforcer.check_workflow_budget(total_cost)
    print_section("Budget check:", f"{'✓ within limits' if budget_ok else '✗ EXCEEDED'}")
    print_section("Fallback model:", enforcer.get_fallback_model())
    print_section("Pattern:", "Cost Governance — per-step tracking, workflow budget enforcement, fallback")


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Run all agentic workflow examples."""
    print()
    print("#" * 70)
    print("#  Agentic Workflows — Usage Examples")
    print("#" * 70)

    examples = [
        example_01_sequential_workflow,
        example_02_routing_workflow,
        example_03_parallel_workflow,
        example_04_evaluator_optimizer,
        example_05_orchestrator_workers,
        example_06_approval_aware_workflow,
        example_07_compensation_aware_workflow,
        example_08_escalation_aware_workflow,
        example_09_context_engineering,
        example_10_cost_governance,
    ]

    for example_fn in examples:
        try:
            example_fn()
        except Exception as exc:
            logger.error(f"{example_fn.__name__} failed: {exc}")
            import traceback
            traceback.print_exc()

    print()
    print("#" * 70)
    print("#  All workflow examples complete!")
    print("#" * 70)
    print()


if __name__ == "__main__":
    main()
