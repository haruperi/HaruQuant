"""SQLite application exports.

The package is intentionally lazy: importing a single mixin such as
`data.database.sqlite.users.UserManager` must not initialize unrelated
risk, execution, or agent modules.
"""

from __future__ import annotations

from typing import Any


_EXPORT_MODULES = {
    "BacktestManager": ".backtests",
    "DatabaseBase": ".base",
    "EdgeDiscoveryManager": ".edge_discovery",
    "LiveTradingManager": ".live_trading",
    "MarketDataManager": ".market_data",
    "OptimizationManager": ".optimization",
    "RiskStorageManager": ".risk_storage",
    "SchemaManager": ".schema",
    "SimulatorManager": ".simulator",
    "SQXManager": ".sqx",
    "StrategyManager": ".strategies",
    "UserAlreadyExistsError": ".base",
    "UserManager": ".users",
}


def _build_sqlite_database() -> type:
    from .backtests import BacktestManager
    from .base import DatabaseBase
    from .edge_discovery import EdgeDiscoveryManager
    from .live_trading import LiveTradingManager
    from .market_data import MarketDataManager
    from .optimization import OptimizationManager
    from .risk_storage import RiskStorageManager
    from .schema import SchemaManager
    from .simulator import SimulatorManager
    from .sqx import SQXManager
    from .strategies import StrategyManager
    from .users import UserManager

    class SQLiteDatabase(
        SchemaManager,
        UserManager,
        StrategyManager,
        SQXManager,
        BacktestManager,
        OptimizationManager,
        RiskStorageManager,
        LiveTradingManager,
        MarketDataManager,
        EdgeDiscoveryManager,
        SimulatorManager,
        DatabaseBase,
    ):
        """Main SQLite database class combining all functionality."""

        pass

    return SQLiteDatabase


def __getattr__(name: str) -> Any:
    if name == "SQLiteDatabase":
        value = _build_sqlite_database()
    else:
        try:
            module_name = _EXPORT_MODULES[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
        from importlib import import_module

        module = import_module(module_name, __name__)
        value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = sorted([*_EXPORT_MODULES, "SQLiteDatabase"])
