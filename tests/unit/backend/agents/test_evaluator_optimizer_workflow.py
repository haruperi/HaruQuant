from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    EvaluatorOptimizerStep,
    EvaluatorOptimizerWorkflowRunner,
    enforce_refine_loop_limit,
)


class IterationRuntime:
    def __init__(self) -> None:
        self.count = 0

    def run(self, *, request, context):  # noqa: ANN001
        self.count += 1
        return AgentExecutionResult(output_payload={"iteration": self.count})


def test_evaluator_optimizer_workflow_runner_stops_when_threshold_met() -> None:
    runtime = IterationRuntime()
    runner = EvaluatorOptimizerWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    result = runner.run(
        generator_step=EvaluatorOptimizerStep(
            runtime_agent=runtime,
            request=ADKRunRequest(
                workflow_id="wf_001",
                correlation_id="corr_001",
                agent_name="research_agent",
                input_payload={},
            ),
        ),
        evaluator=lambda output: 0.9 if output.output_payload["iteration"] >= 2 else 0.4,
        acceptance_threshold=0.8,
        max_iterations=3,
    )

    assert result.iterations == 2
    assert result.terminated_by == "accepted"


def test_refine_loop_guard_blocks_after_max_iterations() -> None:
    decision = enforce_refine_loop_limit(iteration_count=3, max_iterations=3)

    assert decision.allowed is False
    assert decision.reason_codes == ("refine_loop_iteration_limit_reached",)
