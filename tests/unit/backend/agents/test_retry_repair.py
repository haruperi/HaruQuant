"""Unit tests for prompt retry/repair on validation failure."""

from __future__ import annotations

from typing import Any

import pytest

from backend_retiring.agents.runtime.output_validation import (
    CanonicalOutputValidator,
    ContractValidationError,
    RepairAttempt,
    LLMRepairCallable,
)


# ──────────────────────────────────────────────────────────────
# Mock LLM repair callable
# ──────────────────────────────────────────────────────────────

class MockRepairLLM(LLMRepairCallable):
    """Mock LLM that returns predefined repaired payloads."""

    def __init__(self, repairs: list[dict] | None = None) -> None:
        self._repairs = repairs or []
        self._index = 0
        self.calls: list[dict] = []

    def run_repair(
        self,
        *,
        invalid_payload: dict[str, Any],
        error_message: str,
        contract_type: str,
    ) -> dict[str, Any]:
        self.calls.append({
            "invalid_payload": invalid_payload,
            "error_message": error_message,
            "contract_type": contract_type,
        })
        if self._index < len(self._repairs):
            result = self._repairs[self._index]
            self._index += 1
            return result
        return self._repairs[-1] if self._repairs else dict(invalid_payload)


# ──────────────────────────────────────────────────────────────
# Helper: create a minimal valid TradeHypothesis payload
# ──────────────────────────────────────────────────────────────

def _make_valid_th_payload(**overrides: Any) -> dict[str, Any]:
    """Create a minimal valid TradeHypothesis payload."""
    base = {
        "hypothesis_id": "hyp-001",
        "symbol": "EURUSD",
        "direction": "buy",
        "thesis": "EMA crossover with momentum.",
        "entry_rationale": "Breakout retest held.",
        "invalidation_rationale": "Close below EMA(20).",
        "stop_loss_logic": {"type": "swing_low"},
        "take_profit_logic": {"type": "rr_multiple", "multiple": 2.0},
        "holding_horizon": "intraday",
        "confidence": 0.7,
        "calibration_note": "Normal confidence.",
        "evidence": [
            {"source_type": "market", "ref_id": "snap_01", "summary": "Breakout.", "freshness_class": "HOT"}
        ],
        "required_validation_data": ["market_snapshot"],
        "strategy_family": "trend_following",
        "feature_version": "v1",
        "strategy_code_hash": "sha256:abc",
    }
    base.update(overrides)
    return base


def _make_envelope(payload: dict, contract_type: str = "TradeHypothesis") -> dict[str, Any]:
    """Create a valid envelope with the given payload."""
    return {
        "workflow_id": "wf-test",
        "correlation_id": "corr-test",
        "causation_id": "evt-test",
        "timestamp_utc": "2026-04-13T12:00:00Z",
        "originator": {"type": "agent", "id": "test"},
        "environment": "paper",
        "operating_mode": "MODE-002",
        "contract_type": contract_type,
        "schema_version": "1.0.0",
        "payload": payload,
    }


# ──────────────────────────────────────────────────────────────
# Tests: validate_without_retry (baseline)
# ──────────────────────────────────────────────────────────────

def test_validate_succeeds_with_valid_payload() -> None:
    """Valid payload should pass without repair."""
    validator = CanonicalOutputValidator()
    payload = _make_envelope(_make_valid_th_payload())
    result = validator.validate(payload)
    assert result.contract_type == "TradeHypothesis"
    assert result.schema_version == "1.0.0"


def test_validate_fails_with_missing_fields() -> None:
    """Missing required payload fields should fail validation."""
    validator = CanonicalOutputValidator()
    payload = _make_envelope({})  # Empty payload
    with pytest.raises(ContractValidationError):
        validator.validate(payload)


# ──────────────────────────────────────────────────────────────
# Tests: validate_with_retry — success path
# ──────────────────────────────────────────────────────────────

def test_retry_repair_succeeds_on_first_attempt() -> None:
    """Repair should fix a missing field on first attempt."""
    # Payload missing required field (confidence)
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    # Repair LLM provides the full repaired envelope
    repair_llm = MockRepairLLM([
        _make_envelope(_make_valid_th_payload())  # Fully repaired envelope
    ])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=1)
    result, attempts = validator.validate_with_retry(envelope)

    assert result.contract_type == "TradeHypothesis"
    assert len(attempts) == 1
    assert attempts[0].succeeded is True
    assert "confidence" in attempts[0].repaired_payload["payload"]


def test_retry_repair_succeeds_on_second_attempt() -> None:
    """First repair fails, second succeeds."""
    # Payload missing required field
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    # First repair still broken, second fixed
    broken_envelope = _make_envelope(_make_valid_th_payload())
    del broken_envelope["payload"]["confidence"]
    repair_llm = MockRepairLLM([
        broken_envelope,  # Still broken
        _make_envelope(_make_valid_th_payload()),  # Fixed
    ])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=2)
    result, attempts = validator.validate_with_retry(envelope)

    assert result.contract_type == "TradeHypothesis"
    assert len(attempts) == 2
    assert attempts[0].succeeded is False
    assert attempts[1].succeeded is True


# ──────────────────────────────────────────────────────────────
# Tests: validate_with_retry — failure paths
# ──────────────────────────────────────────────────────────────

def test_retry_exhausts_all_attempts() -> None:
    """When all repair attempts fail, ContractValidationError is raised."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    # Repair LLM returns same broken envelope each time
    broken_envelope = _make_envelope(_make_valid_th_payload())
    del broken_envelope["payload"]["confidence"]
    repair_llm = MockRepairLLM([broken_envelope, broken_envelope])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=2)

    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate_with_retry(envelope)

    assert "confidence" in str(exc_info.value)


def test_retry_fails_when_repair_does_not_fix() -> None:
    """When repair doesn't actually fix the issue, validation still fails."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    # Repair LLM returns same broken payload (still missing confidence)
    broken_repair = _make_envelope(_make_valid_th_payload())
    del broken_repair["payload"]["confidence"]
    repair_llm = MockRepairLLM([broken_repair, broken_repair])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=2)

    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate_with_retry(envelope)

    assert "confidence" in str(exc_info.value)


def test_no_repair_llm_raises_immediately() -> None:
    """Without repair LLM, validation errors are raised immediately."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    validator = CanonicalOutputValidator(max_retries=3)  # No repair_llm
    with pytest.raises(ContractValidationError):
        validator.validate_with_retry(envelope)


def test_max_retries_zero_raises_immediately() -> None:
    """With max_retries=0, no repair attempts are made."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    repair_llm = MockRepairLLM([_make_envelope(_make_valid_th_payload())])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=0)
    with pytest.raises(ContractValidationError):
        validator.validate_with_retry(envelope)


def test_repair_llm_failure_is_handled() -> None:
    """When the repair LLM itself fails, the original error is raised."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    class FailingRepairLLM(LLMRepairCallable):
        def run_repair(self, *, invalid_payload, error_message, contract_type):
            raise RuntimeError("LLM service unavailable")

    validator = CanonicalOutputValidator(repair_llm=FailingRepairLLM(), max_retries=1)
    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate_with_retry(envelope)

    assert "repair call also failed" in str(exc_info.value)


# ──────────────────────────────────────────────────────────────
# Tests: RepairAttempt record
# ──────────────────────────────────────────────────────────────

def test_repair_attempt_records_error_and_instruction() -> None:
    """RepairAttempt should record the original error and repair instruction."""
    bad_payload = _make_valid_th_payload()
    del bad_payload["confidence"]
    envelope = _make_envelope(bad_payload)

    # First attempt fails, second succeeds
    broken_envelope = _make_envelope(_make_valid_th_payload())
    del broken_envelope["payload"]["confidence"]

    class PartialRepairLLM(LLMRepairCallable):
        def __init__(self) -> None:
            self._count = 0

        def run_repair(self, *, invalid_payload, error_message, contract_type):
            self._count += 1
            if self._count == 1:
                return broken_envelope  # Still broken
            return _make_envelope(_make_valid_th_payload())  # Fixed

    repair_llm = PartialRepairLLM()
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=2)
    result, attempts = validator.validate_with_retry(envelope)

    assert len(attempts) == 2
    assert attempts[0].succeeded is False
    assert "confidence" in attempts[0].original_error
    assert "Fix the following errors" in attempts[0].repair_instruction
    assert attempts[1].succeeded is True


# ──────────────────────────────────────────────────────────────
# Tests: Integration with ADKRunnerService
# ──────────────────────────────────────────────────────────────

def test_runner_includes_repair_metadata_on_success() -> None:
    """ADKRunResult should include repair_attempted and repair_succeeded."""
    from backend_retiring.agents.runtime.runner import (
        ADKRunRequest,
        ADKRunnerConfig,
        ADKRunnerService,
        AgentExecutionContext,
        AgentExecutionResult,
    )

    class MockAgent:
        def run(self, *, request, context):
            return AgentExecutionResult(
                output_payload=_make_envelope(_make_valid_th_payload()),
                final_state="COMPLETED",
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    validator = CanonicalOutputValidator()
    runner = ADKRunnerService(
        ADKRunnerConfig(runner_name="test"),
        output_validator=validator,
    )
    request = ADKRunRequest(
        workflow_id="wf-repair",
        correlation_id="corr-repair",
        agent_name="strategy_agent",
        input_payload={"symbol": "EURUSD"},
    )

    result = runner.run(agent=MockAgent(), request=request)

    assert result.repair_attempted is False  # No repair needed
    assert result.repair_succeeded is False  # No repair attempted
    assert result.output_payload["contract_type"] == "TradeHypothesis"


def test_runner_attempts_repair_on_validation_failure() -> None:
    """When validation fails, runner should attempt repair."""
    from backend_retiring.agents.runtime.runner import (
        ADKRunRequest,
        ADKRunnerConfig,
        ADKRunnerService,
        AgentExecutionResult,
    )

    class BadAgent:
        def run(self, *, request, context):
            # Missing critical field
            return AgentExecutionResult(
                output_payload=_make_envelope({}),
                final_state="COMPLETED",
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

    repair_llm = MockRepairLLM([_make_envelope(_make_valid_th_payload())])
    validator = CanonicalOutputValidator(repair_llm=repair_llm, max_retries=1)
    runner = ADKRunnerService(
        ADKRunnerConfig(runner_name="test"),
        output_validator=validator,
    )
    request = ADKRunRequest(
        workflow_id="wf-repair",
        correlation_id="corr-repair",
        agent_name="strategy_agent",
        input_payload={"symbol": "EURUSD"},
    )

    result = runner.run(agent=BadAgent(), request=request)

    # The runner attempted repair and it succeeded
    assert result.repair_attempted is True
    assert result.repair_succeeded is True
    assert result.output_payload["contract_type"] == "TradeHypothesis"
