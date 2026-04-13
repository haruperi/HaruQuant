from __future__ import annotations

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    PORTFOLIO_AGENT_INSTRUCTION,
    PortfolioAgentWrapper,
)


class FakePortfolioRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "portfolio_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "EvaluationReport",
                "schema_version": "1.0.0",
                "payload": {
                    "evaluation_id": "eval_001",
                    "target_type": "portfolio_action_review",
                    "target_ref": "portfolio_001",
                    "rubric_name": "portfolio_advisory",
                    "rubric_scores": {"diversification": 0.8, "concentration": 0.6},
                    "overall_score": 0.7,
                    "verdict": "warning",
                    "issues": ["EURUSD concentration elevated"],
                    "improvement_actions": ["Consider hedge or size reduction"],
                    "evaluator_identity": "portfolio_agent",
                    "evaluation_model_id": "gemini-2.5-flash",
                },
            }
        )


def test_portfolio_agent_wrapper_validates_portfolio_proposal_output() -> None:
    wrapper = PortfolioAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakePortfolioRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="portfolio_agent",
            input_payload={"goal": "Assess rebalance options"},
        ),
    )

    assert "advisory recommendations" in PORTFOLIO_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "EvaluationReport"
