"""Latency benchmarks for agent response times."""

from __future__ import annotations

import time

import pytest

from backend.agents.runtime import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionContext,
    AgentExecutionResult,
)


class MockFastAgent:
    """Simulates a fast agent with configurable delay."""
    def __init__(self, delay: float = 0.01) -> None:
        self._delay = delay

    def run(self, *, request, context):
        import time
        time.sleep(self._delay)
        return AgentExecutionResult(
            output_payload={"result": "done"},
            final_state="COMPLETED",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )


def test_fast_agent_latency_p50() -> None:
    """Fast agent should have p50 latency under 100ms."""
    runner = ADKRunnerService(ADKRunnerConfig(runner_name="benchmark"))
    agent = MockFastAgent(delay=0.01)
    latencies = []
    for _ in range(20):
        started = time.monotonic()
        runner.run(
            agent=agent,
            request=ADKRunRequest(
                workflow_id="bench", correlation_id="bench",
                agent_name="mock", input_payload={},
            ),
        )
        latencies.append((time.monotonic() - started) * 1000)

    p50 = sorted(latencies)[len(latencies) // 2]
    assert p50 < 100, f"p50 latency too high: {p50:.0f}ms"


def test_fast_agent_latency_p95() -> None:
    """Fast agent should have p95 latency under 500ms."""
    runner = ADKRunnerService(ADKRunnerConfig(runner_name="benchmark"))
    agent = MockFastAgent(delay=0.01)
    latencies = []
    for _ in range(20):
        started = time.monotonic()
        runner.run(
            agent=agent,
            request=ADKRunRequest(
                workflow_id="bench", correlation_id="bench",
                agent_name="mock", input_payload={},
            ),
        )
        latencies.append((time.monotonic() - started) * 1000)

    p95_idx = int(len(latencies) * 0.95)
    p95 = sorted(latencies)[p95_idx]
    assert p95 < 500, f"p95 latency too high: {p95:.0f}ms"
