from __future__ import annotations

from backend_retiring.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    EXECUTION_AGENT_INSTRUCTION,
    ExecutionAgentWrapper,
)


class FakeExecutionRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "execution_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "ExecutionIntent",
                "schema_version": "1.0.0",
                "payload": {
                    "execution_intent_id": "exec_001",
                    "proposal_id": "prop_001",
                    "risk_decision_id": "risk_dec_001",
                    "broker_action_type": "submit_order",
                    "symbol": "EURUSD",
                    "side": "buy",
                    "size": {"units": 1000},
                    "order_type": "limit",
                    "price_params": {"limit_price": 1.0832},
                    "sl_tp_params": {"stop_loss": 1.08},
                    "idempotency_key": "idem_001",
                    "expiry_time": "2026-04-09T10:05:00Z",
                    "pre_send_validation_snapshot_ref": "presend_001",
                },
            }
        )


def test_execution_agent_wrapper_validates_intent_translation_output() -> None:
    wrapper = ExecutionAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(runner_name="agent-runtime", default_model="gemini-2.5-flash")
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeExecutionRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="execution_agent",
            input_payload={"goal": "Translate approved intent"},
        ),
    )

    assert "never bypass governed execution controls" in EXECUTION_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "ExecutionIntent"
