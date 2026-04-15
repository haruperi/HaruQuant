"""
Strategy Module - Pure Trading Logic.

This module provides a clean, simplified approach to trading strategies.

Core Principles:
1. Strategy = Logic Only: Signal generation and market interpretation
2. DataFrame-based: Signals stored in DataFrame column
3. API: on_init(), on_tick(), on_bar(), get_signal()
4. Vectorized: Calculate all indicators at once
5. StrategyStorage for file management

Key Components:
- BaseStrategy: Abstract base class for all strategies
- StrategyStorage: File storage for strategies
Strategies work across all engines (vectorized, event-driven, live) without modification.
"""

from .adapter import SignalRouter, StrategyAdapter
from .base import BaseStrategy, SignalDict, SignalIntent, StrategyEvent
from .compat_types import PositionTyp, PositionType
from .repro import (
    attach_stability_metadata,
    build_run_manifest,
    compute_config_hash,
    validate_manifest_payload,
)
from .storage import StrategyStorage, storage
from .catalog import (
    StrategyCatalogCreateRequest,
    StrategyCatalogService,
    StrategyCatalogUpdateRequest,
    canonical_json_hash,
    code_hash,
    governance_strategy_id,
)
from .permissions import (
    StrategyPermissionError,
    StrategyRuntimePermissionService,
    assert_strategy_allowed,
)

__version__ = "2.0.0"

__all__ = [
    # Core classes
    "BaseStrategy",
    "SignalIntent",
    "SignalDict",
    "SignalRouter",
    "PositionTyp",
    "PositionType",
    "StrategyAdapter",
    "StrategyEvent",
    "StrategyStorage",
    "StrategyCatalogCreateRequest",
    "StrategyCatalogService",
    "StrategyCatalogUpdateRequest",
    "StrategyPermissionError",
    "StrategyRuntimePermissionService",
    "attach_stability_metadata",
    "assert_strategy_allowed",
    "build_run_manifest",
    "compute_config_hash",
    "canonical_json_hash",
    "code_hash",
    "governance_strategy_id",
    "storage",
    "validate_manifest_payload",
]
