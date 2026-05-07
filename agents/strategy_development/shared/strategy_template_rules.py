"""Strategy template rules for generated HaruQuant strategies."""

from __future__ import annotations

from .constants import REQUIRED_STRATEGY_FILES, STANDARD_ACTIVATOR_COLUMNS, STANDARD_SIGNAL_COLUMNS

BASE_CLASSES = ("BaseStrategy",)
STATEFUL_BASE_CLASSES = ("BaseStrategy", "StatefulStrategyMixin")
REQUIRED_METHODS = ("__init__", "on_init", "on_bar")
STATEFUL_METHODS = ("on_event", "_should_process_event", "_post_process_actions")
LOOKAHEAD_RULES = (
    "If execution occurs at bar N open, signals use bar N-1 or earlier.",
    "Shift indicator values before current-bar execution.",
    "Higher-timeframe features update only after candle close.",
    "README documents execution boundary.",
)
