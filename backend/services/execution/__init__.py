"""Execution service primitives for deterministic validation."""

from .assembler import ExecutionIntentAssemblyConfig, assemble_execution_intent
from .attempts import ExecutionAttemptPersistenceService
from .authority import AuthorityStateView, propagate_authority_state
from .idempotency import generate_execution_idempotency_key
from .metadata_cache import SymbolMetadataCache, SymbolMetadataCacheEntry
from .pre_send import PreSendValidationRequest, run_pre_send_validation
from .readiness import (
    ReadinessAggregateResult,
    ReadinessCheckResult,
    aggregate_readiness_results,
    validate_fill_mode_compatibility,
    validate_market_open,
    validate_price_freshness,
    validate_risk_decision_for_execution,
    validate_stop_and_freeze_levels,
    validate_terminal_connectivity,
    validate_symbol_tradability,
)
from .receipts import ExecutionReceiptService, NormalizedExecutionReceipt
from .send_service import BrokerSendResult, ExecutionSendService

__all__ = [
    "ReadinessAggregateResult",
    "ReadinessCheckResult",
    "ExecutionIntentAssemblyConfig",
    "ExecutionAttemptPersistenceService",
    "AuthorityStateView",
    "BrokerSendResult",
    "ExecutionReceiptService",
    "NormalizedExecutionReceipt",
    "ExecutionSendService",
    "PreSendValidationRequest",
    "aggregate_readiness_results",
    "assemble_execution_intent",
    "generate_execution_idempotency_key",
    "propagate_authority_state",
    "run_pre_send_validation",
    "SymbolMetadataCache",
    "SymbolMetadataCacheEntry",
    "validate_fill_mode_compatibility",
    "validate_market_open",
    "validate_price_freshness",
    "validate_risk_decision_for_execution",
    "validate_stop_and_freeze_levels",
    "validate_terminal_connectivity",
    "validate_symbol_tradability",
]
