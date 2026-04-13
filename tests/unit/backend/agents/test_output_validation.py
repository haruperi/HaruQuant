from __future__ import annotations

import pytest

from backend.agents import CanonicalOutputValidator, ContractValidationError


def test_canonical_output_validator_accepts_registered_contract_payload() -> None:
    validator = CanonicalOutputValidator()

    result = validator.validate(
        {
            "workflow_id": "wf_001",
            "correlation_id": "corr_001",
            "causation_id": "evt_001",
            "timestamp_utc": "2026-04-09T10:00:00Z",
            "originator": {"type": "service", "id": "agent-runtime"},
            "environment": "dev",
            "operating_mode": "MODE-002",
            "contract_type": "WorkflowPlan",
            "schema_version": "1.0.0",
            "payload": {
                "plan_id": "plan_001",
                "selected_pattern": "sequential",
                "phase_steps": [
                    {
                        "step_id": "collect_evidence",
                        "phase": "reason",
                        "owner_agent": "strategy_agent",
                        "goal": "collect evidence",
                        "input_contract_type": "WorkflowIntent",
                        "expected_output_contract_type": "TradeHypothesis",
                    }
                ],
            }
        }
    )

    assert result.contract_type == "WorkflowPlan"
    assert result.schema_version == "1.0.0"
    assert result.validated_model.contract_type == "WorkflowPlan"


def test_canonical_output_validator_rejects_invalid_payload() -> None:
    validator = CanonicalOutputValidator()

    with pytest.raises(ContractValidationError):
        validator.validate(
            {
                "workflow_id": "wf_001",
                "correlation_id": "corr_001",
                "causation_id": "evt_001",
                "timestamp_utc": "2026-04-09T10:00:00Z",
                "originator": {"type": "service", "id": "agent-runtime"},
                "environment": "dev",
                "operating_mode": "MODE-002",
                "contract_type": "WorkflowPlan",
                "schema_version": "1.0.0",
                "payload": {
                    "plan_id": "plan_001",
                    "workflow_type": "trade_review",
                },
            }
        )
