from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    COMPLIANCE_AGENT_INSTRUCTION,
    ComplianceAgentWrapper,
)


class FakeComplianceRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "compliance_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "EvaluationReport",
                "schema_version": "1.0.0",
                "payload": {
                    "evaluation_id": "eval_001",
                    "target_type": "compliance_review",
                    "target_ref": "proposal_001",
                    "rubric_name": "compliance_profile_review",
                    "rubric_scores": {"retention": 1.0, "dual_auth": 0.5},
                    "overall_score": 0.75,
                    "verdict": "warning",
                    "issues": ["Requires compliance sign-off before live release"],
                    "improvement_actions": ["Escalate to compliance queue"],
                    "evaluator_identity": "compliance_agent",
                    "evaluation_model_id": "gemini-2.5-flash",
                },
            }
        )


def test_compliance_agent_wrapper_validates_compliance_review_output() -> None:
    wrapper = ComplianceAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeComplianceRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="compliance_agent",
            input_payload={"goal": "Review compliance requirements"},
        ),
    )

    assert "never silently override or bypass compliance controls" in COMPLIANCE_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "EvaluationReport"
