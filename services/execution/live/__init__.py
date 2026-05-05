"""Live execution runtime built on broker execution services."""

from __future__ import annotations

_EXPORT_MODULES = {
    "Config": "config",
    "StateManager": "state_manager",
    "BarMonitor": "bar_monitor",
    "SignalProcessor": "signal_processor",
    "PositionManager": "position_manager",
    "TradeExecutor": "trade_executor",
    "LiveTradingNotifier": "notification_adapter",
    "MultiStrategyEngine": "engine",
    "StrategyInstance": "engine",
    "LiveTradingSession": "session",
    "ExecutionEngineWrapper": "session",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
