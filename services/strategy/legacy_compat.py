"""Compatibility shims for strategy files saved before the service migration."""

from __future__ import annotations

import sys
import types

from services.utils.logger import logger
from services.indicator import atr, bbands, ema, rsi, sma, wma
from services.strategy.base import (
    BaseStrategy,
    OrderSnapshot,
    PositionSnapshot,
    SignalDict,
    SignalIntent,
    StatefulStrategyMixin,
    StrategyContext,
    StrategyEvent,
    StrategyRuntimeState,
    TradeAction,
    TradeSnapshot,
)
from services.strategy.compat_types import PositionTyp, PositionType


def install_legacy_apps_modules() -> None:
    """Expose the old ``apps.*`` import paths to dynamically loaded strategies.

    Historical strategy files are user artifacts stored on disk. Rewriting them
    during load would change their checksums and governance lineage, so the
    loader provides a narrow import shim instead.
    """

    apps_module = sys.modules.setdefault("apps", types.ModuleType("apps"))

    strategy_module = types.ModuleType("apps.strategy")
    strategy_module.BaseStrategy = BaseStrategy
    strategy_module.Strategy = BaseStrategy
    strategy_module.SignalDict = SignalDict
    strategy_module.SignalIntent = SignalIntent
    strategy_module.StrategyEvent = StrategyEvent
    strategy_module.StrategyContext = StrategyContext
    strategy_module.StrategyRuntimeState = StrategyRuntimeState
    strategy_module.PositionSnapshot = PositionSnapshot
    strategy_module.OrderSnapshot = OrderSnapshot
    strategy_module.TradeSnapshot = TradeSnapshot
    strategy_module.TradeAction = TradeAction
    strategy_module.StatefulStrategyMixin = StatefulStrategyMixin
    strategy_module.__all__ = [
        "BaseStrategy",
        "Strategy",
        "SignalDict",
        "SignalIntent",
        "StrategyEvent",
        "StrategyContext",
        "StrategyRuntimeState",
        "PositionSnapshot",
        "OrderSnapshot",
        "TradeSnapshot",
        "TradeAction",
        "StatefulStrategyMixin",
    ]

    strategy_base_module = types.ModuleType("apps.strategy.base")
    strategy_base_module.BaseStrategy = BaseStrategy
    strategy_base_module.Strategy = BaseStrategy
    strategy_base_module.SignalDict = SignalDict
    strategy_base_module.SignalIntent = SignalIntent
    strategy_base_module.StrategyEvent = StrategyEvent
    strategy_base_module.StrategyContext = StrategyContext
    strategy_base_module.StrategyRuntimeState = StrategyRuntimeState
    strategy_base_module.PositionSnapshot = PositionSnapshot
    strategy_base_module.OrderSnapshot = OrderSnapshot
    strategy_base_module.TradeSnapshot = TradeSnapshot
    strategy_base_module.TradeAction = TradeAction
    strategy_base_module.StatefulStrategyMixin = StatefulStrategyMixin
    strategy_base_module.__all__ = strategy_module.__all__

    indicator_module = types.ModuleType("apps.indicator")
    indicator_module.atr = atr
    indicator_module.bbands = bbands
    indicator_module.ema = ema
    indicator_module.rsi = rsi
    indicator_module.sma = sma
    indicator_module.wma = wma
    indicator_module.__all__ = ["atr", "bbands", "ema", "rsi", "sma", "wma"]

    utils_module = sys.modules.setdefault("apps.utils", types.ModuleType("apps.utils"))
    logger_module = types.ModuleType("apps.utils.logger")
    logger_module.logger = logger

    trading_module = types.ModuleType("apps.trading")
    trading_module.PositionType = PositionType
    trading_module.PositionTyp = PositionTyp

    trade_module = types.ModuleType("apps.trade")
    trade_module.PositionType = PositionType
    trade_module.PositionTyp = PositionTyp

    apps_module.strategy = strategy_module
    apps_module.indicator = indicator_module
    apps_module.utils = utils_module
    apps_module.trading = trading_module
    apps_module.trade = trade_module
    utils_module.logger = logger_module

    sys.modules["apps.strategy"] = strategy_module
    sys.modules["apps.strategy.base"] = strategy_base_module
    sys.modules["apps.indicator"] = indicator_module
    sys.modules["apps.utils"] = utils_module
    sys.modules["apps.utils.logger"] = logger_module
    sys.modules["apps.trading"] = trading_module
    sys.modules["apps.trade"] = trade_module
