"""Shared constants for Strategy Creation Department agents."""

from __future__ import annotations

DEPARTMENT_NAME = "Strategy Creation Department"
STRATEGY_CREATION_VERSION = "strategy_creation_v1"
DEFAULT_SYMBOL = "EURUSD"
DEFAULT_TIMEFRAME = "H1"
STANDARD_SIGNAL_COLUMNS = (
    "entry_signal",
    "exit_signal",
    "pending_signal",
    "cancel_pending_signal",
    "pending_signal_2",
    "cancel_pending_signal_2",
    "price",
    "price_2",
    "stop_loss",
    "take_profit",
    "signal_reason",
    "setup_id",
    "group_id",
)
STANDARD_ACTIVATOR_COLUMNS = (
    "buy_setup_active",
    "sell_setup_active",
    "buy_add_active",
    "sell_add_active",
    "buy_exit_active",
    "sell_exit_active",
    "buy_pyramid_active",
    "sell_pyramid_active",
    "buy_martingale_active",
    "sell_martingale_active",
    "buy_decompose_active",
    "sell_decompose_active",
    "buy_trail_active",
    "sell_trail_active",
)
REQUIRED_STRATEGY_FILES = (
    "strategy.py",
    "config.py",
    "README.md",
    "tests/test_params.py",
    "tests/test_on_bar.py",
    "tests/test_no_lookahead.py",
)
FORBIDDEN_CODE_MARKERS = ("MetaTrader5", "mt5.", "ctrader", "execute_order", "approve_risk")
