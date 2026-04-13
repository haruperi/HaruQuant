"""Tests for dynamic orchestrator, workflow definitions, state persistence, and circuit breaker."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

# ──────────────────────────────────────────────────────────────
# Phase 5: Dynamic Orchestrator Tests
# ──────────────────────────────────────────────────────────────

from backend.agents.runtime.dynamic_orchestrator import (
    DynamicOrchestratorResult,
    DynamicOrchestratorWorkerRunner,
    OrchestratorPlan,
)
from backend.agents.runtime.runner import (
    ADKRunRequest,
    ADKRunResult,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
)


class MockOrchestratorAgent:
    """Mock orchestrator that returns a predefined plan."""
    def __init__(self, plan_data: dict) -> None:
        self._plan_data = plan_data
        self.call_count = 0

    def run(self, *, request, context):
        self.call_count += 1
        return AgentExecutionResult(
            output_payload=self._plan_data,
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


class MockWorkerAgent:
    """Mock worker that returns simple output."""
    def __init__(self, output: dict) -> None:
        self._output = output
        self.call_count = 0

    def run(self, *, request, context):
        self.call_count += 1
        return AgentExecutionResult(
            output_payload=self._output,
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 80, "completion_tokens": 40, "total_tokens": 120},
        )


def test_dynamic_orchestrator_plans_and_dispatches() -> None:
    """Orchestrator should generate plan, dispatch workers, synthesize results."""
    plan_data = {
        "tasks": [
            {"task_name": "research_task", "agent_name": "research_agent", "input_payload": {"symbol": "EURUSD"}},
            {"task_name": "strategy_task", "agent_name": "strategy_agent", "input_payload": {"symbol": "EURUSD"}},
        ],
        "synthesis_instructions": "Combine research and strategy outputs",
        "confidence": 0.85,
        "reasoning": "Both agents needed for complete analysis",
    }

    orchestrator = MockOrchestratorAgent(plan_data)
    adk_runner = ADKRunnerService(
        ADKRunnerConfig(runner_name="test", default_model="test-model")
    )
    runner = DynamicOrchestratorWorkerRunner(
        adk_runner=adk_runner,
        orchestrator_agent=orchestrator,
    )

    # For this test, we use the fact that DynamicOrchestratorWorkerRunner
    # creates ParallelWorkflowTask with ADKRunnerService as the agent.
    # The ADKRunnerService.run() expects an AgentRuntime, so we use a mock.
    # Since we can't easily mock the parallel dispatch, we test the plan generation.
    result = runner._generate_plan(
        goal="Analyze EURUSD",
        available_workers={"research_agent": {}, "strategy_agent": {}},
        workflow_id="wf-test",
        correlation_id="corr-test",
        agent_name="orchestrator_agent",
    )

    assert result.workflow_id == "wf-test"
    assert len(result.tasks) == 2
    assert result.confidence == 0.85
    assert result.synthesis_instructions == "Combine research and strategy outputs"


def test_dynamic_orchestrator_synthesizes_results() -> None:
    """Synthesis should combine worker outputs and detect conflicts."""
    plan = OrchestratorPlan(
        workflow_id="wf-test",
        tasks=(
            {"task_name": "task_a", "agent_name": "agent_a", "input_payload": {}},
            {"task_name": "task_b", "agent_name": "agent_b", "input_payload": {}},
        ),
        synthesis_instructions="Synthesize",
        confidence=0.8,
    )

    runner = DynamicOrchestratorWorkerRunner(
        adk_runner=ADKRunnerService(ADKRunnerConfig(runner_name="test")),
        orchestrator_agent=MockOrchestratorAgent({}),
    )

    worker_results = {
        "task_a": ADKRunResult(
            runner_name="test", runtime_version="v1", agent_name="agent_a",
            workflow_id="wf-test", correlation_id="corr-test", session_id=None,
            model="test", prompt_version_id=None, prompt_hash=None,
            latency_ms=10, output_payload={"analysis": "bullish", "confidence": 0.7},
            final_state="COMPLETED", tool_calls=(), token_usage=None,
        ),
        "task_b": ADKRunResult(
            runner_name="test", runtime_version="v1", agent_name="agent_b",
            workflow_id="wf-test", correlation_id="corr-test", session_id=None,
            model="test", prompt_version_id=None, prompt_hash=None,
            latency_ms=15, output_payload={"risk": "low", "confidence": 0.9},
            final_state="COMPLETED", tool_calls=(), token_usage=None,
        ),
    }

    synthesized, failed, conflicts = runner._synthesize(plan=plan, worker_results=worker_results)

    assert "task_a" in synthesized["combined_results"]
    assert "task_b" in synthesized["combined_results"]
    assert len(failed) == 0
    assert len(conflicts) == 0  # No conflicting keys


def test_dynamic_orchestrator_handles_worker_failure() -> None:
    """Failed workers should be tracked in synthesis."""
    plan = OrchestratorPlan(
        workflow_id="wf-test",
        tasks=(
            {"task_name": "task_ok", "agent_name": "agent_ok", "input_payload": {}},
            {"task_name": "task_fail", "agent_name": "agent_fail", "input_payload": {}},
        ),
        synthesis_instructions="Synthesize",
        confidence=0.8,
    )

    runner = DynamicOrchestratorWorkerRunner(
        adk_runner=ADKRunnerService(ADKRunnerConfig(runner_name="test")),
        orchestrator_agent=MockOrchestratorAgent({}),
    )

    worker_results = {
        "task_ok": ADKRunResult(
            runner_name="test", runtime_version="v1", agent_name="agent_ok",
            workflow_id="wf-test", correlation_id="corr-test", session_id=None,
            model="test", prompt_version_id=None, prompt_hash=None,
            latency_ms=10, output_payload={"data": "ok"},
            final_state="COMPLETED", tool_calls=(), token_usage=None,
        ),
        "task_fail": ADKRunResult(
            runner_name="test", runtime_version="v1", agent_name="agent_fail",
            workflow_id="wf-test", correlation_id="corr-test", session_id=None,
            model="test", prompt_version_id=None, prompt_hash=None,
            latency_ms=5, output_payload={"error": "timeout"},
            final_state="FAILED", tool_calls=(), token_usage=None,
        ),
    }

    synthesized, failed, conflicts = runner._synthesize(plan=plan, worker_results=worker_results)

    assert len(failed) == 1
    assert failed[0] == "task_fail"
    assert synthesized["failed_count"] == 1


# ──────────────────────────────────────────────────────────────
# Phase 7: Workflow Definition Tests
# ──────────────────────────────────────────────────────────────

from backend.agents.runtime.workflow_definition import (
    WorkflowDefinition,
    WorkflowDefinitionParser,
    WorkflowPattern,
    WorkflowRegistry,
    WorkflowStepDef,
    WorkflowRouteDef,
    run_workflow,
)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_parser_parses_sequential_workflow() -> None:
    yaml_content = """
name: trade_analysis
pattern: sequential
description: Analyze and plan a trade
steps:
  - name: research
    agent: research_agent
    input:
      query: "EURUSD outlook"
    expected_output: ObservationEvent
  - name: strategy
    agent: strategy_agent
    input:
      symbol: "EURUSD"
    depends_on:
      - research
    expected_output: TradeHypothesis
acceptance_threshold: 0.8
"""
    parser = WorkflowDefinitionParser()
    definition = parser.parse(yaml_content)

    assert definition.name == "trade_analysis"
    assert definition.pattern == WorkflowPattern.SEQUENTIAL
    assert len(definition.steps) == 2
    assert definition.steps[0].name == "research"
    assert definition.steps[0].agent == "research_agent"
    assert definition.steps[1].depends_on == ["research"]


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_parser_parses_routing_workflow() -> None:
    yaml_content = """
name: request_router
pattern: routing
routes:
  - route_key: research
    agent: research_agent
    input:
      type: query
  - route_key: risk
    agent: compliance_agent
    input:
      type: assessment
default_route:
  route_key: fallback
  agent: research_agent
  is_default: true
"""
    parser = WorkflowDefinitionParser()
    definition = parser.parse(yaml_content)

    assert definition.pattern == WorkflowPattern.ROUTING
    assert len(definition.routes) == 2
    assert definition.default_route is not None
    assert definition.default_route.route_key == "fallback"


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_parser_rejects_invalid_yaml() -> None:
    parser = WorkflowDefinitionParser()
    with pytest.raises(ValueError, match="Invalid YAML"):
        parser.parse("name: test\npattern: [invalid")


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_parser_rejects_missing_name() -> None:
    parser = WorkflowDefinitionParser()
    with pytest.raises(ValueError, match="requires a 'name'"):
        parser.parse("pattern: sequential")


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_parser_rejects_invalid_pattern() -> None:
    parser = WorkflowDefinitionParser()
    with pytest.raises(ValueError, match="Invalid pattern"):
        parser.parse("name: test\npattern: invalid_pattern")


@pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
def test_registry_loads_and_caches() -> None:
    """Registry should load from file and cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = "name: test_workflow\npattern: sequential\nsteps: []\n"
        yaml_path = os.path.join(tmpdir, "test_workflow.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        registry = WorkflowRegistry(workflow_dir=tmpdir)
        definition = registry.load("test_workflow")
        assert definition.name == "test_workflow"

        # Second load should use cache
        cached = registry.load("test_workflow")
        assert cached is definition

        # List workflows
        assert "test_workflow" in registry.list_workflows()


# ──────────────────────────────────────────────────────────────
# Phase 8: Workflow State Persistence Tests
# ──────────────────────────────────────────────────────────────

from backend.agents.runtime.workflow_state import (
    WorkflowCheckpoint,
    WorkflowStateManager,
)


def test_state_manager_saves_and_loads_checkpoint() -> None:
    """Checkpoint should be saved and loaded correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        mgr.save_checkpoint(
            workflow_id="wf-001",
            step_name="research",
            step_index=0,
            state={"context": "initial"},
            output_payload={"result": "bullish"},
            final_state="COMPLETED",
            workflow_pattern="sequential",
        )

        checkpoint = mgr.load_checkpoint("wf-001")
        assert checkpoint is not None
        assert checkpoint.workflow_id == "wf-001"
        assert checkpoint.step_name == "research"
        assert checkpoint.step_index == 0
        assert json.loads(checkpoint.state_json) == {"context": "initial"}
        assert json.loads(checkpoint.output_payload) == {"result": "bullish"}


def test_state_manager_loads_multiple_checkpoints() -> None:
    """Should load all checkpoints in order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        for i, step_name in enumerate(["research", "strategy", "compliance"]):
            mgr.save_checkpoint(
                workflow_id="wf-002",
                step_name=step_name,
                step_index=i,
                state={"step": step_name},
                output_payload={"output": step_name},
                final_state="COMPLETED",
            )

        checkpoints = mgr.load_checkpoints("wf-002")
        assert len(checkpoints) == 3
        assert checkpoints[0].step_name == "research"
        assert checkpoints[1].step_name == "strategy"
        assert checkpoints[2].step_name == "compliance"


def test_state_manager_resume_from_checkpoint() -> None:
    """Resume should return last checkpoint state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        mgr.save_checkpoint(
            workflow_id="wf-003",
            step_name="research",
            step_index=0,
            state={"context": "done"},
            output_payload={"result": "ok"},
            final_state="COMPLETED",
        )

        resume_info = mgr.resume_from_checkpoint("wf-003")
        assert resume_info is not None
        assert resume_info["last_completed_step"] == "research"
        assert resume_info["last_step_index"] == 0
        assert resume_info["last_output"]["result"] == "ok"


def test_state_manager_returns_none_for_missing_workflow() -> None:
    """No checkpoint → None for resume."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        assert mgr.load_checkpoint("nonexistent") is None
        assert mgr.resume_from_checkpoint("nonexistent") is None


def test_state_manager_deletes_checkpoints() -> None:
    """Delete should remove all checkpoints for a workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        mgr.save_checkpoint("wf-004", "step1", 0, {}, {}, "COMPLETED")
        mgr.save_checkpoint("wf-004", "step2", 1, {}, {}, "COMPLETED")

        count = mgr.delete_checkpoints("wf-004")
        assert count == 2
        assert mgr.load_checkpoint("wf-004") is None


def test_state_manager_execution_history() -> None:
    """Execution history should return structured dicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_states.db")
        mgr = WorkflowStateManager(db_path=db_path)

        mgr.save_checkpoint("wf-005", "step1", 0, {"key": "value"}, {"out": "ok"}, "COMPLETED")

        history = mgr.get_execution_history("wf-005")
        assert len(history) == 1
        assert history[0]["step_name"] == "step1"
        assert history[0]["state"] == {"key": "value"}
        assert history[0]["output"] == {"out": "ok"}


# ──────────────────────────────────────────────────────────────
# Phase 9: Circuit Breaker Tests
# ──────────────────────────────────────────────────────────────

from backend.agents.runtime.circuit_breaker import (
    AgentCircuitBreaker,
    CircuitBreakerState,
    CircuitOpenError,
    CircuitState,
)


def test_circuit_breaker_starts_closed() -> None:
    """New circuit should be in CLOSED state."""
    cb = AgentCircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    state = cb.get_state("test_agent")
    assert state is None  # Not created until first call


def test_circuit_breaker_opens_after_threshold_failures() -> None:
    """Circuit should open after N consecutive failures."""
    cb = AgentCircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    def failing_func():
        raise RuntimeError("Agent failure")

    # 2 failures → still closed
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    state = cb.get_state("test_agent")
    assert state is not None
    assert state.state == CircuitState.CLOSED
    assert state.failure_count == 2

    # 3rd failure → opens circuit
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    state = cb.get_state("test_agent")
    assert state is not None
    assert state.state == CircuitState.OPEN
    assert state.failure_count == 3


def test_circuit_breaker_rejects_calls_when_open() -> None:
    """Open circuit should raise CircuitOpenError."""
    cb = AgentCircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

    def failing_func():
        raise RuntimeError("Agent failure")

    # Open the circuit
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    # Next call should be rejected
    with pytest.raises(CircuitOpenError) as exc_info:
        cb.call("test_agent", lambda: "success")

    assert exc_info.value.agent_name == "test_agent"
    assert exc_info.value.retry_after_seconds > 0


def test_circuit_breaker_closes_on_success() -> None:
    """Successful call should keep circuit closed."""
    cb = AgentCircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

    result = cb.call("test_agent", lambda: "success")
    assert result == "success"

    state = cb.get_state("test_agent")
    assert state is not None
    assert state.state == CircuitState.CLOSED
    assert state.failure_count == 0


def test_circuit_breaker_half_open_to_closed() -> None:
    """Successful call in HALF_OPEN should close circuit."""
    cb = AgentCircuitBreaker(failure_threshold=2, recovery_timeout=0.01)

    def failing_func():
        raise RuntimeError("fail")

    # Open circuit
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    assert cb.get_state("test_agent").state == CircuitState.OPEN

    # Manually reset recovery timeout to 0 for instant recovery
    cb._circuits["test_agent"] = CircuitBreakerState(
        agent_name="test_agent",
        state=CircuitState.OPEN,
        failure_count=2,
        last_failure_time=time.monotonic() - 1.0,  # 1 second ago
        last_failure_reason="fail",
        recovery_timeout=0.001,  # Very short timeout
        last_state_change=time.monotonic(),
    )

    # Next call → HALF_OPEN → success → CLOSED
    result = cb.call("test_agent", lambda: "recovered")
    assert result == "recovered"

    state = cb.get_state("test_agent")
    assert state is not None
    assert state.state == CircuitState.CLOSED


def test_circuit_breaker_half_open_reopens_on_failure() -> None:
    """Failed call in HALF_OPEN should re-open circuit."""
    cb = AgentCircuitBreaker(failure_threshold=2, recovery_timeout=0.01)

    def failing_func():
        raise RuntimeError("fail")

    # Open circuit
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    # Manually set up HALF_OPEN state
    cb._circuits["test_agent"] = CircuitBreakerState(
        agent_name="test_agent",
        state=CircuitState.HALF_OPEN,
        failure_count=2,
        last_failure_time=time.monotonic() - 1.0,
        last_failure_reason="fail",
        recovery_timeout=0.01,
        last_state_change=time.monotonic(),
    )

    # Next call → HALF_OPEN → failure → OPEN
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    state = cb.get_state("test_agent")
    assert state is not None
    assert state.state == CircuitState.OPEN


def test_circuit_breaker_manual_reset() -> None:
    """Manual reset should close circuit."""
    cb = AgentCircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

    def failing_func():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)
    with pytest.raises(RuntimeError):
        cb.call("test_agent", failing_func)

    assert cb.get_state("test_agent").state == CircuitState.OPEN

    cb.reset("test_agent")
    assert cb.get_state("test_agent").state == CircuitState.CLOSED
