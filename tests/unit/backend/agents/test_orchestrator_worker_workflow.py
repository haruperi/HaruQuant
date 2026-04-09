from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    OrchestratorWorkerTask,
    OrchestratorWorkerWorkflowRunner,
)


class WorkerRuntime:
    def __init__(self, name: str) -> None:
        self.name = name

    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(output_payload={"worker": self.name})


def test_orchestrator_worker_workflow_runner_executes_task_graph() -> None:
    runner = OrchestratorWorkerWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    results = runner.run(
        tasks=(
            OrchestratorWorkerTask(
                worker_name="research_agent",
                runtime_agent=WorkerRuntime("research_agent"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="research_agent",
                    input_payload={},
                ),
            ),
            OrchestratorWorkerTask(
                worker_name="strategy_agent",
                runtime_agent=WorkerRuntime("strategy_agent"),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="strategy_agent",
                    input_payload={},
                ),
            ),
        )
    )

    assert sorted(results.keys()) == ["research_agent", "strategy_agent"]
    assert results["strategy_agent"].output_payload["worker"] == "strategy_agent"
