from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    REGIME_AGENT_INSTRUCTION,
    RegimeAgentWrapper,
)


class FakeRegimeRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "regime_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "regime_summary",
                    "severity": "info",
                    "source": "regime_agent",
                    "payload_ref_or_inline": {"regime": "trend", "confidence": 0.81},
                    "authority_state": {"advisory_only": True},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_regime_agent_wrapper_validates_regime_output_schema() -> None:
    wrapper = RegimeAgentWrapper(
        runner=ADKRunnerService(ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeRegimeRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="regime_agent",
            input_payload={"goal": "Summarize market regime"},
        ),
    )

    assert "market regime conditions" in REGIME_AGENT_INSTRUCTION
    assert result.output_payload["contract_type"] == "ObservationEvent"
