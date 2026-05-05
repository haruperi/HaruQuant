"""Tests for async workflow runners (Phase 10)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

import pytest

from backend_retiring.agents.runtime.async_workflows import (
    AsyncParallelResult,
    AsyncParallelWorkflowRunner,
    AsyncParallelWorkflowTask,
    AsyncSequentialResult,
    AsyncSequentialWorkflowRunner,
    AsyncSequentialWorkflowStep,
)


@dataclass(frozen=True)
class MockAsyncResult:
    output_payload: dict
    final_state: str = "COMPLETED"
    token_usage: dict | None = None


class MockAsyncAgent:
    """Mock async agent with configurable delay."""
    def __init__(self, output: dict, delay: float = 0.0) -> None:
        self._output = output
        self._delay = delay
        self.call_count = 0

    async def run_async(self, *, request, context):
        self.call_count += 1
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        return MockAsyncResult(output_payload=self._output)


class FailingAsyncAgent:
    """Mock async agent that always fails."""
    def __init__(self, error: str = "Agent failure") -> None:
        self._error = error
        self.call_count = 0

    async def run_async(self, *, request, context):
        self.call_count += 1
        raise RuntimeError(self._error)


def test_async_parallel_runner_executes_tasks_concurrently() -> None:
    """Tasks should execute concurrently (total time < sum of individual times)."""
    async def _run():
        runner = AsyncParallelWorkflowRunner()
        tasks = (
            AsyncParallelWorkflowTask(
                task_name="task_a",
                runtime_agent=MockAsyncAgent({"result": "a"}, delay=0.1),
                request=None,
            ),
            AsyncParallelWorkflowTask(
                task_name="task_b",
                runtime_agent=MockAsyncAgent({"result": "b"}, delay=0.1),
                request=None,
            ),
            AsyncParallelWorkflowTask(
                task_name="task_c",
                runtime_agent=MockAsyncAgent({"result": "c"}, delay=0.1),
                request=None,
            ),
        )
        import time
        start = time.monotonic()
        result = await runner.run(tasks=tasks)
        elapsed = time.monotonic() - start
        return result, elapsed

    result, elapsed = asyncio.run(_run())

    assert len(result.results) == 3
    assert "task_a" in result.results
    assert "task_b" in result.results
    assert "task_c" in result.results
    # Parallel execution should be faster than sequential (0.3s)
    assert elapsed < 0.25, f"Tasks ran sequentially ({elapsed:.2f}s)"


def test_async_parallel_runner_handles_task_failure() -> None:
    """Failed task should be tracked, not crash the runner."""
    async def _run():
        runner = AsyncParallelWorkflowRunner()
        tasks = (
            AsyncParallelWorkflowTask(
                task_name="ok_task",
                runtime_agent=MockAsyncAgent({"result": "ok"}),
                request=None,
            ),
            AsyncParallelWorkflowTask(
                task_name="fail_task",
                runtime_agent=FailingAsyncAgent("boom"),
                request=None,
            ),
        )
        return await runner.run(tasks=tasks)

    result = asyncio.run(_run())

    assert "ok_task" in result.results
    assert "fail_task" in result.failed_tasks
    assert len(result.failed_tasks) == 1


def test_async_sequential_runner_passes_context() -> None:
    """Each step should receive prior_steps in metadata."""
    async def _run():
        runner = AsyncSequentialWorkflowRunner()

        class ContextCapturingAsyncAgent:
            def __init__(self) -> None:
                self.captured_metadata = []

            async def run_async(self, *, request, context):
                self.captured_metadata.append(dict(request.metadata) if request.metadata else {})
                return MockAsyncResult(output_payload={"step": len(self.captured_metadata)})

        agent1 = ContextCapturingAsyncAgent()
        agent2 = ContextCapturingAsyncAgent()
        agent3 = ContextCapturingAsyncAgent()

        from backend_retiring.agents.runtime.runner import ADKRunRequest

        steps = (
            AsyncSequentialWorkflowStep(
                step_name="step1",
                runtime_agent=agent1,
                request=ADKRunRequest(
                    workflow_id="wf", correlation_id="corr",
                    agent_name="agent1", input_payload={},
                ),
            ),
            AsyncSequentialWorkflowStep(
                step_name="step2",
                runtime_agent=agent2,
                request=ADKRunRequest(
                    workflow_id="wf", correlation_id="corr",
                    agent_name="agent2", input_payload={},
                ),
            ),
            AsyncSequentialWorkflowStep(
                step_name="step3",
                runtime_agent=agent3,
                request=ADKRunRequest(
                    workflow_id="wf", correlation_id="corr",
                    agent_name="agent3", input_payload={},
                ),
            ),
        )
        return await runner.run(steps=steps), agent1, agent2, agent3

    result, agent1, agent2, agent3 = asyncio.run(_run())

    assert len(result.results) == 3
    assert result.final_state == "COMPLETED"

    # Step 1 should have no prior_steps
    assert agent1.captured_metadata[0].get("prior_steps") == {}
    # Step 2 should have step1
    assert "step1" in agent2.captured_metadata[0].get("prior_steps", {})
    # Step 3 should have step1 and step2
    prior = agent3.captured_metadata[0].get("prior_steps", {})
    assert "step1" in prior
    assert "step2" in prior


def test_async_sequential_runner_stops_on_failure() -> None:
    """Failed step should stop the chain."""
    async def _run():
        runner = AsyncSequentialWorkflowRunner()
        steps = (
            AsyncSequentialWorkflowStep(
                step_name="step1",
                runtime_agent=MockAsyncAgent({"data": "ok"}),
                request=None,
            ),
            AsyncSequentialWorkflowStep(
                step_name="step2",
                runtime_agent=FailingAsyncAgent("boom"),
                request=None,
            ),
            AsyncSequentialWorkflowStep(
                step_name="step3",
                runtime_agent=MockAsyncAgent({"data": "should_not_run"}),
                request=None,
            ),
        )
        return await runner.run(steps=steps)

    result = asyncio.run(_run())

    assert len(result.results) == 2  # Only 2 steps ran
    assert result.final_state == "FAILED"
