"""SQLITE application."""

from .backtests import BacktestManager
from .base import DatabaseBase, UserAlreadyExistsError
from .live_trading import LiveTradingManager
from .market_data import MarketDataManager
from .optimization import OptimizationManager
from .schema import SchemaManager
from .strategies import StrategyManager
from .users import UserManager


class SQLiteDatabase(
    SchemaManager,
    UserManager,
    StrategyManager,
    BacktestManager,
    OptimizationManager,
    LiveTradingManager,
    MarketDataManager,
    DatabaseBase,
):
    """
    Main SQLite database class combining all functionality.

    Inherits from connection management and all domain-specific mixins.
    """

    pass


__all__ = [
    "SQLiteDatabase",
    "DatabaseBase",
    "UserAlreadyExistsError",
]
