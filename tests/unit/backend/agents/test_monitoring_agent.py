from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    MONITORING_AGENT_INSTRUCTION,
    MonitoringAgentWrapper,
)


class FakeMonitoringRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "monitoring_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "IncidentAlert",
                "schema_version": "1.0.0",
                "payload": {
                    "incident_id": "inc_001",
                    "severity": "warning",
                    "alert_type": "STALE_MARKET_DATA",
                    "summary": "Market snapshot exceeded freshness budget.",
                    "source": "monitoring_agent",
                    "related_refs": ["mkt_001"],
                    "recommended_action": "Refresh market snapshot before continuing.",
                    "incident_state": "open",
                },
            }
        )


def test_monitoring_agent_wrapper_validates_alert_classification_output() -> None:
    wrapper = MonitoringAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeMonitoringRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="monitoring_agent",
            input_payload={"event": "stale market data"},
        ),
    )

    assert "classify alerts clearly" in MONITORING_AGENT_INSTRUCTION
    assert result.output_payload["contract_type"] == "IncidentAlert"
    assert result.output_payload["payload"]["severity"] == "warning"
