"""Execution service primitives for deterministic validation."""

from __future__ import annotations

_EXPORT_MODULES = {
    "ExecutionIntentAssemblyConfig": "assembler",
    "assemble_execution_intent": "assembler",
    "ExecutionAttemptPersistenceService": "attempts",
    "AuthorityStateView": "authority",
    "propagate_authority_state": "authority",
    "generate_execution_idempotency_key": "idempotency",
    "SymbolMetadataCache": "metadata_cache",
    "SymbolMetadataCacheEntry": "metadata_cache",
    "PreSendValidationRequest": "pre_send",
    "run_pre_send_validation": "pre_send",
    "ReadinessAggregateResult": "readiness",
    "ReadinessCheckResult": "readiness",
    "aggregate_readiness_results": "readiness",
    "validate_fill_mode_compatibility": "readiness",
    "validate_market_open": "readiness",
    "validate_price_freshness": "readiness",
    "validate_risk_decision_for_execution": "readiness",
    "validate_stop_and_freeze_levels": "readiness",
    "validate_terminal_connectivity": "readiness",
    "validate_symbol_tradability": "readiness",
    "ExecutionReceiptService": "receipts",
    "NormalizedExecutionReceipt": "receipts",
    "BrokerSendResult": "send_service",
    "ExecutionSendService": "send_service",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    """Load execution symbols lazily to keep package imports side-effect light."""
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
