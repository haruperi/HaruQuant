from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    VOLATILITY_AGENT_INSTRUCTION,
    VolatilityAgentWrapper,
)


class FakeVolatilityRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "volatility_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "volatility_summary",
                    "severity": "info",
                    "source": "volatility_agent",
                    "payload_ref_or_inline": {"atr_regime": "elevated", "volatility_score": 0.67},
                    "authority_state": {"advisory_only": True},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_volatility_agent_wrapper_validates_volatility_summary_schema() -> None:
    wrapper = VolatilityAgentWrapper(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeVolatilityRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="volatility_agent",
            input_payload={"goal": "Summarize volatility"},
        ),
    )

    assert "volatility" in VOLATILITY_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "ObservationEvent"
