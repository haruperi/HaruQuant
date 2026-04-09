from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    SequentialWorkflowRunner,
    SequentialWorkflowStep,
)


class OrderedRuntime:
    def __init__(self, name: str, sink: list[str]) -> None:
        self.name = name
        self.sink = sink

    def run(self, *, request, context):  # noqa: ANN001
        self.sink.append(self.name)
        return AgentExecutionResult(
            output_payload={"step": self.name, "input": request.input_payload},
        )


def test_sequential_workflow_runner_executes_steps_in_order() -> None:
    order: list[str] = []
    runner = SequentialWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    results = runner.run(
        steps=(
            SequentialWorkflowStep(
                step_name="reason",
                runtime_agent=OrderedRuntime("reason", order),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="strategy_agent",
                    input_payload={"phase": "reason"},
                ),
            ),
            SequentialWorkflowStep(
                step_name="verify",
                runtime_agent=OrderedRuntime("verify", order),
                request=ADKRunRequest(
                    workflow_id="wf_001",
                    correlation_id="corr_001",
                    agent_name="risk_governor_agent",
                    input_payload={"phase": "verify"},
                ),
            ),
        )
    )

    assert order == ["reason", "verify"]
    assert [result.output_payload["step"] for result in results] == ["reason", "verify"]
