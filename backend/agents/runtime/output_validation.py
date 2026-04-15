"""Canonical output validation with retry/repair on validation failure.

When output validation fails, feed the error back to the LLM for
self-correction instead of hard-failing. This improves resilience
by giving the model a chance to fix schema violations before
propagating errors upstream.
"""

from __future__ import annotations

from backend.common.logger import logger
import json
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from pydantic import BaseModel

from backend.contracts import (
    ContractValidationError,
    SchemaRegistryService,
    load_initial_schema_registry_seeds,
    validate_contract_payload,
)


@dataclass(frozen=True)
class CanonicalValidationResult:
    contract_type: str
    schema_version: str
    validated_model: BaseModel


@dataclass(frozen=True)
class RepairAttempt:
    """Record of a single repair attempt."""
    original_error: str
    repair_instruction: str
    repaired_payload: dict[str, Any]
    succeeded: bool


class LLMRepairCallable(Protocol):
    """Protocol for an LLM that can repair invalid payloads."""

    def run_repair(
        self,
        *,
        invalid_payload: dict[str, Any],
        error_message: str,
        contract_type: str,
    ) -> dict[str, Any]: ...


class CanonicalOutputValidator:
    """Validate agent outputs against the canonical schema registry.

    Supports optional retry/repair: when validation fails, the validator
    can ask an LLM to fix the payload before raising the error.
    """

    def __init__(
        self,
        registry: SchemaRegistryService | None = None,
        repair_llm: LLMRepairCallable | None = None,
        max_retries: int = 1,
    ) -> None:
        self._registry = registry or SchemaRegistryService(load_initial_schema_registry_seeds())
        self._repair_llm = repair_llm
        self._max_retries = max(max_retries, 0)

    def validate(self, payload: dict[str, Any]) -> CanonicalValidationResult:
        """Validate without retry — raises on first failure."""
        validated_model = validate_contract_payload(payload, self._registry)
        return CanonicalValidationResult(
            contract_type=str(payload["contract_type"]),
            schema_version=str(payload["schema_version"]),
            validated_model=validated_model,
        )

    def validate_with_retry(
        self,
        payload: dict[str, Any],
        repair_prompt: str | None = None,
    ) -> tuple[CanonicalValidationResult, list[RepairAttempt]]:
        """Validate with automatic repair on failure.

        Returns:
            (result, repair_attempts) — repair_attempts is empty on success.

        Raises:
            ContractValidationError: If validation fails after max_retries.
        """
        repair_attempts: list[RepairAttempt] = []

        # Try initial validation
        last_error: ContractValidationError | None = None
        try:
            return self.validate(payload), repair_attempts
        except ContractValidationError as exc:
            if self._max_retries <= 0 or self._repair_llm is None:
                raise
            last_error = exc

        # Attempt repairs
        current_payload = dict(payload)
        for attempt_num in range(self._max_retries):
            error_msg = str(last_error)
            repair_instruction = repair_prompt or (
                f"Your previous output failed validation. Fix the following errors:\n"
                f"{error_msg}\n\n"
                f"Return ONLY the corrected JSON matching the {current_payload.get('contract_type', 'unknown')} schema. "
                f"Do not include any explanation — only valid JSON."
            )

            # Call LLM to repair
            try:
                repaired = self._repair_llm.run_repair(
                    invalid_payload=current_payload,
                    error_message=error_msg,
                    contract_type=current_payload.get("contract_type", "unknown"),
                )
            except Exception as repair_exc:
                repair_attempts.append(RepairAttempt(
                    original_error=error_msg,
                    repair_instruction=repair_instruction,
                    repaired_payload=current_payload,
                    succeeded=False,
                ))
                # Repair call itself failed — re-raise original error
                raise ContractValidationError(
                    f"Validation failed and repair call also failed: {repair_exc}"
                ) from repair_exc

            # Try validating the repaired payload
            try:
                result = self.validate(repaired)
                repair_attempts.append(RepairAttempt(
                    original_error=error_msg,
                    repair_instruction=repair_instruction,
                    repaired_payload=repaired,
                    succeeded=True,
                ))
                return result, repair_attempts
            except ContractValidationError as new_exc:
                repair_attempts.append(RepairAttempt(
                    original_error=error_msg,
                    repair_instruction=repair_instruction,
                    repaired_payload=repaired,
                    succeeded=False,
                ))
                last_error = new_exc
                current_payload = repaired

        # All retries exhausted
        raise last_error
