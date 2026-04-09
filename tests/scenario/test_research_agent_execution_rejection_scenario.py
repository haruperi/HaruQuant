from __future__ import annotations

import pytest

from backend.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    ResearchAgentWrapper,
)


class _ExecutionIntentResearchRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_exec_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "research_agent"},
                "environment": "prod",
                "operating_mode": "MODE-003",
                "contract_type": "ExecutionIntent",
                "schema_version": "1.0.0",
                "payload": {
                    "execution_intent_id": "exec_001",
                    "proposal_id": "prop_001",
                    "risk_decision_id": "risk_001",
                    "broker_action_type": "submit_order",
                    "symbol": "EURUSD",
                    "side": "buy",
                    "size": {"units": 1000},
                    "order_type": "market",
                    "price_params": {"entry_price": 1.0842},
                    "sl_tp_params": {},
                    "idempotency_key": "idem_001",
                    "expiry_time": "2026-04-09T10:05:00Z",
                    "pre_send_validation_snapshot_ref": "snap_001",
                },
            }
        )


def test_research_agent_attempt_to_issue_execution_instruction_is_rejected() -> None:
    wrapper = ResearchAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )

    with pytest.raises(ValueError, match="ResearchAgent must emit ObservationEvent outputs"):
        wrapper.execute(
            runtime_agent=_ExecutionIntentResearchRuntime(),
            request=ADKRunRequest(
                workflow_id="wf_001",
                correlation_id="corr_001",
                agent_name="research_agent",
                input_payload={"query": "Summarize EURUSD catalysts"},
            ),
        )

