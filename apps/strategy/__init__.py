"""
Strategy Module - Pure Trading Logic.

This module provides a clean, simplified approach to trading strategies.

Core Principles:
1. Strategy = Logic Only: Signal generation and market interpretation
2. DataFrame-based: Signals stored in DataFrame column
3. API: on_init(), on_tick(), on_bar(), on_trade(), on_order_update(), on_timer(), on_shutdown(), get_signal()
4. Vectorized: Calculate all indicators at once
5. StrategyStorage for file management

Key Components:
- BaseStrategy: Abstract base class for all strategies
- StrategyEvent: Canonical event contract
- SignalIntent: Canonical signal intent contract
- StrategyAdapter: Signal/event normalization adapter
- SignalRouter: Intent forwarding/validation helper
- Repro helpers: run manifest/version binding and stability metadata
- StrategyStorage: File storage for strategies
Strategies work across all engines (vectorized, event-driven, live) without modification.
"""

from .base import BaseStrategy, SignalIntent, StrategyEvent
from .adapter import StrategyAdapter, SignalRouter
from .repro import attach_stability_metadata, build_run_manifest, compute_config_hash, validate_manifest_payload
from .storage import StrategyStorage, storage

__version__ = "2.0.0"

__all__ = [
    # Core classes
    "BaseStrategy",
    "SignalIntent",
    "StrategyEvent",
    "StrategyAdapter",
    "SignalRouter",
    "compute_config_hash",
    "build_run_manifest",
    "attach_stability_metadata",
    "validate_manifest_payload",
    "StrategyStorage",
    "storage",
]
