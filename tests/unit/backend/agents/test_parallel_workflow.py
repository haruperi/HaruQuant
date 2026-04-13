from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    ParallelWorkflowRunner,
    ParallelWorkflowTask,
)


class NamedRuntime:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(output_payload={"task": self.name})


class MetadataCapturingRuntime:
    def __init__(self) -> None:
        self.captured_metadata: list[dict] = []

    def run(self, *, request, context):  # noqa: ANN001
        self.captured_metadata.append(dict(request.metadata))
        return AgentExecutionResult(output_payload={"ok": True})


def test_parallel_workflow_runner_fans_out_and_fans_in_results() -> None:
    runner = ParallelWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    results = runner.run(
        tasks=(
            ParallelWorkflowTask(
                task_name="volatility",
                runtime_agent=NamedRuntime("volatility"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="volatility_agent",
                    input_payload={},
                ),
            ),
            ParallelWorkflowTask(
                task_name="regime",
                runtime_agent=NamedRuntime("regime"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="regime_agent",
                    input_payload={},
                ),
            ),
        )
    )

    assert sorted(results.keys()) == ["regime", "volatility"]
    assert results["volatility"].output_payload["task"] == "volatility"
    assert results["regime"].output_payload["task"] == "regime"


def test_parallel_workflow_injects_peer_tasks_metadata() -> None:
    """Each task should receive peer_tasks metadata with names of other tasks."""
    capturer = MetadataCapturingRuntime()
    runner = ParallelWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    runner.run(
        tasks=(
            ParallelWorkflowTask(
                task_name="fetch_data",
                runtime_agent=capturer,
                request=ADKRunRequest(
                    workflow_id="wf-parallel",
                    correlation_id="corr-parallel",
                    agent_name="data_agent",
                    input_payload={},
                ),
            ),
            ParallelWorkflowTask(
                task_name="check_risk",
                runtime_agent=capturer,
                request=ADKRunRequest(
                    workflow_id="wf-parallel",
                    correlation_id="corr-parallel",
                    agent_name="risk_agent",
                    input_payload={},
                ),
            ),
        )
    )

    # Both tasks should have received peer_tasks metadata
    for meta in capturer.captured_metadata:
        assert "peer_tasks" in meta
        assert set(meta["peer_tasks"]) == {"fetch_data", "check_risk"}
