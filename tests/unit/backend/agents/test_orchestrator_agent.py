from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    ORCHESTRATOR_AGENT_INSTRUCTION,
    OrchestratorAgentWrapper,
)


class FakeOrchestratorRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "orchestrator_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "WorkflowPlan",
                "schema_version": "1.0.0",
                "payload": {
                    "plan_id": "plan_001",
                    "selected_pattern": "sequential_review",
                    "phase_steps": [
                        {
                            "phase": "reason",
                            "owner": "strategy_agent",
                            "goal": "collect evidence",
                        }
                    ],
                },
            }
        )


def test_orchestrator_agent_wrapper_validates_goal_decomposition_stub() -> None:
    wrapper = OrchestratorAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeOrchestratorRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="orchestrator_agent",
            input_payload={"goal": "Review EURUSD setup"},
        ),
    )

    assert "never perform broker actions directly" in ORCHESTRATOR_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "WorkflowPlan"
    assert result.output_payload["payload"]["phase_steps"][0]["owner"] == "strategy_agent"
