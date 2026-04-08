"""Shared domain error hierarchy for migration-era services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class ErrorContext:
    """Normalized context attached to an application error."""

    workflow_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    environment: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorEnvelope:
    """Serializable error payload used across internal boundaries."""

    code: str
    category: str
    message: str
    retryable: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    context: ErrorContext = field(default_factory=ErrorContext)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "retryable": self.retryable,
            "details": dict(self.details),
            "context": {
                "workflow_id": self.context.workflow_id,
                "correlation_id": self.context.correlation_id,
                "causation_id": self.context.causation_id,
                "environment": self.context.environment,
                "metadata": dict(self.context.metadata),
            },
        }


class HaruCoreError(Exception):
    """Base shared application error for new migration components."""

    category = "core"

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: Optional[Mapping[str, Any]] = None,
        context: Optional[ErrorContext] = None,
    ) -> None:
        self.envelope = ErrorEnvelope(
            code=code,
            category=self.category,
            message=message,
            retryable=retryable,
            details=dict(details or {}),
            context=context or ErrorContext(),
        )
        super().__init__(f"[{self.category}:{code}] {message}")

    @property
    def code(self) -> str:
        return self.envelope.code

    @property
    def retryable(self) -> bool:
        return self.envelope.retryable

    def to_dict(self) -> Dict[str, Any]:
        return self.envelope.to_dict()


class DomainError(HaruCoreError):
    """Business/domain rule failure."""

    category = "domain"


class ValidationError(HaruCoreError):
    """Input or contract validation failure."""

    category = "validation"


class PolicyError(HaruCoreError):
    """Policy or governance enforcement failure."""

    category = "policy"


class BrokerError(HaruCoreError):
    """Broker- or execution-bound integration failure."""

    category = "broker"


class InfrastructureError(HaruCoreError):
    """Infrastructure, storage, or dependency failure."""

    category = "infrastructure"


def envelope_from_mapping(payload: Mapping[str, Any]) -> ErrorEnvelope:
    """Rebuild an error envelope from a plain mapping."""

    context_payload = payload.get("context", {}) or {}
    return ErrorEnvelope(
        code=str(payload["code"]),
        category=str(payload["category"]),
        message=str(payload["message"]),
        retryable=bool(payload.get("retryable", False)),
        details=dict(payload.get("details", {}) or {}),
        context=ErrorContext(
            workflow_id=str(context_payload.get("workflow_id", "")),
            correlation_id=str(context_payload.get("correlation_id", "")),
            causation_id=str(context_payload.get("causation_id", "")),
            environment=str(context_payload.get("environment", "")),
            metadata=dict(context_payload.get("metadata", {}) or {}),
        ),
    )
