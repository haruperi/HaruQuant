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


class MetadataCapturingRuntime:
    def __init__(self) -> None:
        self.captured_metadata: list[dict] = []

    def run(self, *, request, context):  # noqa: ANN001
        self.captured_metadata.append(dict(request.metadata))
        return AgentExecutionResult(output_payload={"iteration": len(self.captured_metadata)})


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


def test_evaluator_optimizer_injects_refinement_context() -> None:
    """Generator should receive refinement metadata on retry iterations."""
    capturer = MetadataCapturingRuntime()
    runner = EvaluatorOptimizerWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    # Force 2 iterations: first fails (0.3), second passes (0.9)
    scores = [0.3, 0.9]
    score_idx = [0]

    def evaluator(output) -> float:
        s = scores[min(score_idx[0], len(scores) - 1)]
        score_idx[0] += 1
        return s

    runner.run(
        generator_step=EvaluatorOptimizerStep(
            runtime_agent=capturer,
            request=ADKRunRequest(
                workflow_id="wf-refine",
                correlation_id="corr-refine",
                agent_name="generator_agent",
                input_payload={},
            ),
        ),
        evaluator=evaluator,
        acceptance_threshold=0.8,
        max_iterations=3,
    )

    # First iteration should NOT have refinement context
    assert "refinement_iteration" not in capturer.captured_metadata[0]

    # Second iteration SHOULD have refinement context
    assert "refinement_iteration" in capturer.captured_metadata[1]
    assert capturer.captured_metadata[1]["refinement_iteration"] == 1
    assert capturer.captured_metadata[1]["previous_score"] == 0.3
