from __future__ import annotations

from backend_retiring.agents import (
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


class CapturingRuntime:
    """Captures request metadata for verification of context chaining."""
    def __init__(self) -> None:
        self.captured_metadata: list[dict] = []

    def run(self, *, request, context):  # noqa: ANN001
        self.captured_metadata.append(dict(request.metadata))
        return AgentExecutionResult(
            output_payload={"result": f"done_{len(self.captured_metadata)}"},
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


def test_sequential_workflow_injects_prior_steps_context() -> None:
    """Step 2 should receive step 1's output in metadata['prior_steps']."""
    capturer = CapturingRuntime()
    runner = SequentialWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        )
    )

    runner.run(
        steps=(
            SequentialWorkflowStep(
                step_name="fetch_data",
                runtime_agent=capturer,
                request=ADKRunRequest(
                    workflow_id="wf-chain",
                    correlation_id="corr-chain",
                    agent_name="data_agent",
                    input_payload={"task": "fetch"},
                ),
            ),
            SequentialWorkflowStep(
                step_name="analyze",
                runtime_agent=capturer,
                request=ADKRunRequest(
                    workflow_id="wf-chain",
                    correlation_id="corr-chain",
                    agent_name="analysis_agent",
                    input_payload={"task": "analyze"},
                ),
            ),
        )
    )

    # Step 1 should have no prior_steps
    assert "prior_steps" in capturer.captured_metadata[0]
    assert capturer.captured_metadata[0]["prior_steps"] == {}

    # Step 2 should have step 1's output in prior_steps
    assert "prior_steps" in capturer.captured_metadata[1]
    prior = capturer.captured_metadata[1]["prior_steps"]
    assert "fetch_data" in prior
    assert prior["fetch_data"]["output"]["result"] == "done_1"
    assert prior["fetch_data"]["state"] == "COMPLETED"


def test_sequential_workflow_stops_on_invalid_step_output() -> None:
    """When step output fails validation and validate_before_next is True, chain stops."""
    from backend_retiring.agents.runtime.output_validation import CanonicalOutputValidator

    class FailingRuntime:
        """Produces wrong contract_type to trigger validation failure."""
        def __init__(self) -> None:
            self.call_count = 0

        def run(self, *, request, context):
            self.call_count += 1
            return AgentExecutionResult(
                output_payload={
                    "contract_type": "WrongType",
                    "schema_version": "1.0.0",
                    "payload": {"data": f"step_{self.call_count}"},
                },
                final_state="COMPLETED",
                tool_calls=(),
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    validator = CanonicalOutputValidator()
    runner = SequentialWorkflowRunner(
        ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        output_validator=validator,
    )

    failing_rt = FailingRuntime()
    results = runner.run(
        steps=(
            SequentialWorkflowStep(
                step_name="step_one",
                runtime_agent=failing_rt,
                request=ADKRunRequest(
                    workflow_id="wf-val",
                    correlation_id="corr-val",
                    agent_name="strategy_agent",
                    input_payload={},
                ),
                expected_output_contract_type="TradeHypothesis",
                validate_before_next=True,
            ),
            SequentialWorkflowStep(
                step_name="step_two",
                runtime_agent=failing_rt,
                request=ADKRunRequest(
                    workflow_id="wf-val",
                    correlation_id="corr-val",
                    agent_name="strategy_agent",
                    input_payload={},
                ),
                expected_output_contract_type="TradeHypothesis",
                validate_before_next=True,
            ),
        )
    )

    # Only first step should run — validation fails, chain stops
    assert len(results) == 1
    assert failing_rt.call_count == 1  # Second step was never called
