"""End-to-end workflow integration tests.

Tests full multi-stage workflows with contract validation at each stage,
context chaining, error handling, and failure cases.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.agents.runtime.runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
)
from backend.agents.runtime.output_validation import CanonicalOutputValidator
from backend.agents.runtime.workflows import (
    EvaluatorOptimizerResult,
    EvaluatorOptimizerStep,
    EvaluatorOptimizerWorkflowRunner,
    ParallelAggregateResult,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
    RoutingWorkflowBranch,
    RoutingWorkflowRunner,
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
)


# ──────────────────────────────────────────────────────────────
# Mock agents that produce valid contract outputs
# ──────────────────────────────────────────────────────────────

def _make_envelope(contract_type: str, payload: dict) -> dict:
    return {
        "workflow_id": "wf-int",
        "correlation_id": "corr-int",
        "causation_id": "evt-001",
        "timestamp_utc": "2026-04-13T12:00:00Z",
        "originator": {"type": "agent", "id": "test"},
        "environment": "paper",
        "operating_mode": "MODE-002",
        "contract_type": contract_type,
        "schema_version": "1.0.0",
        "payload": payload,
    }


class MockResearchAgent:
    """Produces valid ObservationEvent."""
    def run(self, *, request, context):
        return AgentExecutionResult(
            output_payload=_make_envelope("ObservationEvent", {
                "observation_id": "obs-001",
                "agent_name": "research_agent",
                "event_type": "research_finding",
                "severity": "info",
                "observation": "EURUSD trending bullish.",
                "evidence": [{"source": "market", "value": "bullish"}],
                "assumptions": ["trend persists"],
                "limitations": ["short lookback"],
                "freshness": "2026-04-13T12:00:00Z",
                "metadata": {"confidence": 0.8},
            }),
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


class MockStrategyAgent:
    """Produces valid TradeHypothesis."""
    def run(self, *, request, context):
        return AgentExecutionResult(
            output_payload=_make_envelope("TradeHypothesis", {
                "hypothesis_id": "hyp-001",
                "symbol": "EURUSD",
                "direction": "buy",
                "thesis": "Trend continuation.",
                "entry_rationale": "Higher highs confirmed.",
                "invalidation_rationale": "Break below support.",
                "stop_loss_logic": {"type": "swing_low"},
                "take_profit_logic": {"type": "rr_multiple", "multiple": 2.0},
                "holding_horizon": "intraday",
                "confidence": 0.75,
                "calibration_note": "Normal.",
                "evidence": [{"source_type": "market", "ref_id": "snap_01", "summary": "Confirmed", "freshness_class": "HOT"}],
                "required_validation_data": ["market_snapshot"],
                "strategy_family": "trend_following",
                "feature_version": "v1",
                "strategy_code_hash": "sha256:abc",
            }),
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


class MockComplianceAgent:
    """Produces valid EvaluationReport."""
    def run(self, *, request, context):
        return AgentExecutionResult(
            output_payload=_make_envelope("EvaluationReport", {
                "evaluation_id": "eval-001",
                "target_type": "trade_hypothesis",
                "target_ref": "hyp-001",
                "rubric_name": "compliance",
                "rubric_scores": {"risk": 0.9, "evidence": 0.8},
                "overall_score": 0.85,
                "verdict": "pass",
                "issues": [],
                "improvement_actions": [],
                "evaluator_identity": "compliance_agent",
                "evaluation_model_id": "v1",
            }),
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120},
        )


class _CapturingAgent:
    """Captures request metadata for context chaining verification."""
    def __init__(self, contract_type: str, payload: dict) -> None:
        self._output = _make_envelope(contract_type, payload)
        self.captured_metadata: list[dict] = []

    def run(self, *, request, context):
        self.captured_metadata.append(dict(request.metadata) if request.metadata else {})
        return AgentExecutionResult(
            output_payload=self._output,
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


# ──────────────────────────────────────────────────────────────
# Test 1: Full sequential workflow (research → strategy → compliance)
# ──────────────────────────────────────────────────────────────

def test_sequential_full_chain_with_validation() -> None:
    """End-to-end: research → strategy → compliance, each with contract validation."""
    validator = CanonicalOutputValidator()
    runner = SequentialWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
        output_validator=validator,
    )

    results = runner.run(steps=(
        SequentialWorkflowStep(
            step_name="research",
            runtime_agent=MockResearchAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="research_agent",
                input_payload={"query": "EURUSD outlook"},
            ),
            expected_output_contract_type="ObservationEvent",
        ),
        SequentialWorkflowStep(
            step_name="strategy",
            runtime_agent=MockStrategyAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="strategy_agent",
                input_payload={"symbol": "EURUSD"},
            ),
            expected_output_contract_type="TradeHypothesis",
        ),
        SequentialWorkflowStep(
            step_name="compliance",
            runtime_agent=MockComplianceAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="compliance_agent",
                input_payload={"hypothesis_id": "hyp-001"},
            ),
            expected_output_contract_type="EvaluationReport",
        ),
    ))

    # All 3 steps completed
    assert len(results) == 3
    assert results[0].output_payload["contract_type"] == "ObservationEvent"
    assert results[1].output_payload["contract_type"] == "TradeHypothesis"
    assert results[2].output_payload["contract_type"] == "EvaluationReport"


def test_sequential_chain_stops_on_contract_mismatch() -> None:
    """When step output contract doesn't match expected type, chain stops."""
    runner = SequentialWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
    )

    results = runner.run(steps=(
        SequentialWorkflowStep(
            step_name="step1",
            runtime_agent=MockResearchAgent(),  # Produces ObservationEvent
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="research_agent",
                input_payload={},
            ),
            expected_output_contract_type="TradeHypothesis",  # Wrong!
        ),
        SequentialWorkflowStep(
            step_name="step2",
            runtime_agent=MockStrategyAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="strategy_agent",
                input_payload={},
            ),
            expected_output_contract_type="TradeHypothesis",
        ),
    ))

    # Only first step ran (validation failed)
    assert len(results) == 1
    assert results[0].output_payload["contract_type"] == "ObservationEvent"


# ──────────────────────────────────────────────────────────────
# Test 2: Parallel fan-out/fan-in with contract validation
# ──────────────────────────────────────────────────────────────

def test_parallel_fan_out_fan_in() -> None:
    """Fan-out to independent agents, fan-in with aggregated results."""
    runner = ParallelWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
    )

    aggregate = runner.run(tasks=(
        ParallelWorkflowTask(
            task_name="research",
            runtime_agent=MockResearchAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="research_agent",
                input_payload={"symbol": "EURUSD"},
            ),
            expected_output_contract_type="ObservationEvent",
        ),
        ParallelWorkflowTask(
            task_name="compliance",
            runtime_agent=MockComplianceAgent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="compliance_agent",
                input_payload={"symbol": "EURUSD"},
            ),
            expected_output_contract_type="EvaluationReport",
        ),
    ))

    assert "research" in aggregate.results
    assert "compliance" in aggregate.results
    assert len(aggregate.failed_tasks) == 0
    assert len(aggregate.timed_out_tasks) == 0


# ──────────────────────────────────────────────────────────────
# Test 3: Evaluator-Optimizer with rubric-based refinement
# ──────────────────────────────────────────────────────────────

def test_evaluator_optimizer_with_threshold() -> None:
    """Generator produces output, evaluator scores it, loop until threshold met."""
    runner = EvaluatorOptimizerWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
    )

    call_count = [0]

    def generator_agent():
        class Agent:
            def run(self, *, request, context):
                call_count[0] += 1
                return AgentExecutionResult(
                    output_payload={"iteration": call_count[0], "quality": min(0.9, 0.5 + call_count[0] * 0.15)},
                    final_state="COMPLETED",
                    token_usage={"total_tokens": 150},
                )
        return Agent()

    def evaluator(result):
        return result.output_payload.get("quality", 0.0)

    result = runner.run(
        generator_step=EvaluatorOptimizerStep(
            runtime_agent=generator_agent(),
            request=ADKRunRequest(
                workflow_id="wf-int",
                correlation_id="corr-int",
                agent_name="strategy_agent",
                input_payload={"goal": "Generate hypothesis"},
            ),
        ),
        evaluator=evaluator,
        acceptance_threshold=0.78,
        max_iterations=5,
    )

    assert result.terminated_by == "accepted"
    assert result.evaluation_scores[-1] >= 0.78
    assert result.iterations >= 2  # At least 2 iterations needed to reach 0.78


# ──────────────────────────────────────────────────────────────
# Test 4: Routing with intent-based branch execution
# ──────────────────────────────────────────────────────────────

def test_routing_with_branch_selection() -> None:
    """Route request to correct branch based on route_key."""
    runner = RoutingWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
    )

    # Route to research
    result = runner.run(
        route_key="research",
        branches=(
            RoutingWorkflowBranch(
                route_key="research",
                runtime_agent=MockResearchAgent(),
                request=ADKRunRequest(
                    workflow_id="wf-int",
                    correlation_id="corr-int",
                    agent_name="research_agent",
                    input_payload={},
                ),
            ),
            RoutingWorkflowBranch(
                route_key="compliance",
                runtime_agent=MockComplianceAgent(),
                request=ADKRunRequest(
                    workflow_id="wf-int",
                    correlation_id="corr-int",
                    agent_name="compliance_agent",
                    input_payload={},
                ),
            ),
        ),
    )

    assert result.output_payload["contract_type"] == "ObservationEvent"


def test_routing_with_default_fallback() -> None:
    """Unmatched route should use default branch."""
    from backend.agents.runtime.workflows import RoutingWorkflowBranch

    default = RoutingWorkflowBranch(
        route_key="default",
        runtime_agent=MockResearchAgent(),
        request=ADKRunRequest(
            workflow_id="wf-int",
            correlation_id="corr-int",
            agent_name="research_agent",
            input_payload={"fallback": True},
        ),
    )

    runner = RoutingWorkflowRunner(
        ADKRunnerService(ADKRunnerConfig(runner_name="integration-test")),
        default_branch=default,
    )

    result = runner.run(
        route_key="unknown_intent",
        branches=(
            RoutingWorkflowBranch(
                route_key="research",
                runtime_agent=MockResearchAgent(),
                request=ADKRunRequest(
                    workflow_id="wf-int",
                    correlation_id="corr-int",
                    agent_name="research_agent",
                    input_payload={},
                ),
            ),
        ),
    )

    assert result.output_payload["contract_type"] == "ObservationEvent"
    assert result.output_payload["payload"].get("fallback") is True
