from __future__ import annotations

from backend_retiring.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    RESEARCH_AGENT_INSTRUCTION,
    ResearchAgentWrapper,
)


class FakeResearchRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "research_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ObservationEvent",
                "schema_version": "1.0.0",
                "payload": {
                    "observation_id": "obs_001",
                    "observation_type": "research_summary",
                    "severity": "info",
                    "source": "approved_sources",
                    "payload_ref_or_inline": {
                        "evidence_refs": ["evidence_001"],
                        "assumptions": ["No unscheduled macro shock"],
                        "limitations": ["News feed coverage limited to approved set"],
                    },
                    "authority_state": {"grounded": True},
                    "freshness_status": "fresh",
                    "observed_at": "2026-04-09T10:00:00Z",
                },
            }
        )


def test_research_agent_wrapper_validates_evidence_and_freshness_output() -> None:
    wrapper = ResearchAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeResearchRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="research_agent",
            input_payload={"query": "Summarize EURUSD catalysts"},
        ),
    )

    assert "never emit execution instructions" in RESEARCH_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "ObservationEvent"
    assert result.output_payload["payload"]["freshness_status"] == "fresh"
