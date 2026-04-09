"""Shared core primitives for the agentic migration foundation."""

from .errors import (
    BrokerError,
    DomainError,
    ErrorContext,
    ErrorEnvelope,
    InfrastructureError,
    PolicyError,
    ValidationError,
)
from .logging import WorkflowLogContext, bind_log_context, get_service_logger
from .optimistic import ConcurrencyState, StaleVersionError, apply_version_update, ensure_version
from .secrets import SecretRef, SecretRotationPolicy, redact_secret_mapping, select_active_secret_version
from .telemetry import (
    CounterMetric,
    InMemoryTelemetry,
    SpanRecord,
    TelemetryEvent,
    TimerMetric,
)
from .time_utils import (
    BOARD_BASELINE_TTL_POLICY,
    BoardBaselineArtifactWindow,
    BoardBaselineFreshnessEvaluation,
    Clock,
    FixedClock,
    FreshnessWindow,
    SystemClock,
    evaluate_board_baseline_freshness,
    is_stale,
)
from .ids import generate_id, generate_prefixed_id

__all__ = [
    "BrokerError",
    "DomainError",
    "ErrorContext",
    "ErrorEnvelope",
    "InfrastructureError",
    "PolicyError",
    "ValidationError",
    "WorkflowLogContext",
    "bind_log_context",
    "get_service_logger",
    "CounterMetric",
    "InMemoryTelemetry",
    "SpanRecord",
    "TelemetryEvent",
    "TimerMetric",
    "BOARD_BASELINE_TTL_POLICY",
    "BoardBaselineArtifactWindow",
    "BoardBaselineFreshnessEvaluation",
    "Clock",
    "FixedClock",
    "FreshnessWindow",
    "SystemClock",
    "evaluate_board_baseline_freshness",
    "is_stale",
    "generate_id",
    "generate_prefixed_id",
    "SecretRef",
    "SecretRotationPolicy",
    "redact_secret_mapping",
    "select_active_secret_version",
    "ConcurrencyState",
    "StaleVersionError",
    "apply_version_update",
    "ensure_version",
]
