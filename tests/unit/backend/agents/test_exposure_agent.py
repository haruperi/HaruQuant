from __future__ import annotations

from backend_retiring.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    EXPOSURE_AGENT_INSTRUCTION,
    ExposureAgentWrapper,
)


class FakeExposureRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "exposure_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "exposure_summary",
                    "severity": "warning",
                    "source": "exposure_agent",
                    "payload_ref_or_inline": {"gross_exposure": 2.3, "largest_symbol_share": 0.41},
                    "authority_state": {"advisory_only": True},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_exposure_agent_wrapper_validates_exposure_output_schema() -> None:
    wrapper = ExposureAgentWrapper(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeExposureRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="exposure_agent",
            input_payload={"goal": "Summarize exposure concentrations"},
        ),
    )

    assert "marginal risk contribution" in EXPOSURE_AGENT_INSTRUCTION
    assert result.output_payload["contract_type"] == "ObservationEvent"
