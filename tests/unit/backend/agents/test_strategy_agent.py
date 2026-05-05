from __future__ import annotations

from backend_retiring.agents import (
    ADKRunRequest,
    ADKRunnerConfig,
    ADKRunnerService,
    AgentExecutionResult,
    CanonicalOutputValidator,
    STRATEGY_AGENT_INSTRUCTION,
    StrategyAgentWrapper,
)


class FakeStrategyRuntime:
    def run(self, *, request, context):  # noqa: ANN001
        return AgentExecutionResult(
            output_payload={
                "workflow_id": request.workflow_id,
                "correlation_id": request.correlation_id,
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "agent", "id": "strategy_agent"},
                "environment": "paper",
                "operating_mode": "MODE-002",
                "contract_type": "TradeHypothesis",
                "schema_version": "1.0.0",
                "payload": {
                    "hypothesis_id": "hyp_001",
                    "symbol": "EURUSD",
                    "direction": "buy",
                    "thesis": "Momentum regime remains constructive.",
                    "entry_rationale": "Retest held above prior resistance.",
                    "invalidation_rationale": "Break below retest zone invalidates setup.",
                    "stop_loss_logic": {"type": "swing_low_buffer", "buffer_pips": 8},
                    "take_profit_logic": {"type": "rr_multiple", "multiple": 2.0},
                    "holding_horizon": "intraday",
                    "confidence": 0.74,
                    "calibration_note": "Confidence adjusted for event risk.",
                    "evidence": [
                        {
                            "source_type": "market",
                            "ref_id": "snap_01",
                            "summary": "Breakout and retest confirmed.",
                            "freshness_class": "HOT",
                        }
                    ],
                    "required_validation_data": [
                        "market_snapshot",
                        "account_snapshot",
                        "portfolio_snapshot",
                    ],
                    "strategy_family": "trend_following",
                    "feature_version": "feat_v3",
                    "strategy_code_hash": "sha256:abc123",
                },
            }
        )


def test_strategy_agent_wrapper_validates_hypothesis_output_schema() -> None:
    wrapper = StrategyAgentWrapper(
        runner=ADKRunnerService(
            ADKRunnerConfig(
                runner_name="agent-runtime",
                default_model="gemini-2.5-flash",
            )
        ),
        output_validator=CanonicalOutputValidator(),
    )

    result = wrapper.execute(
        runtime_agent=FakeStrategyRuntime(),
        request=ADKRunRequest(
            workflow_id="wf_001",
            correlation_id="corr_001",
            agent_name="strategy_agent",
            input_payload={"goal": "Generate trade hypothesis"},
        ),
    )

    assert "never emit broker orders" in STRATEGY_AGENT_INSTRUCTION.lower()
    assert result.output_payload["contract_type"] == "TradeHypothesis"
    assert result.output_payload["payload"]["symbol"] == "EURUSD"
