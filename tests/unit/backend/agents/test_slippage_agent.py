from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    SLIPPAGE_AGENT_INSTRUCTION,
    SlippageAgentWrapper,
)


class FakeSlippageRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "slippage_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "slippage_assessment",
                    "severity": "warning",
                    "source": "slippage_agent",
                    "payload_ref_or_inline": {"spread_bps": 4.2, "expected_slippage_bps": 3.1},
                    "authority_state": {"advisory_only": True},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_slippage_agent_wrapper_validates_slippage_assessment_schema() -> None:
    wrapper = SlippageAgentWrapper(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeSlippageRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="slippage_agent",
            input_payload={"goal": "Summarize slippage risk"},
        ),
    )

    assert "slippage and spread conditions" in SLIPPAGE_AGENT_INSTRUCTION
    assert result.output_payload["contract_type"] == "ObservationEvent"
