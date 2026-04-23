"""Simulation service for HaruQuant.

Session lifecycle, coordinator, runtime, and trade service for paper trading simulation.
"""

from .session_coordinator import SessionCoordinator
from .session_manager import SimulatorSessionManager
from .session_backend import (
    SessionMetadata,
    SessionRuntimeStore,
    SQLiteSessionRuntimeStore,
)
from .config import (
    AccountConfig,
    DataConfig,
    ExecutionConfig,
    PositionSizeConfig,
    ReportingConfig,
    SimulationConfig,
    SimulationConfigError,
    StrategyConfig,
)
from .models import (
    SimulationStartRequest,
    SimulationUpdateRequest,
    ManualTradeRequest,
    PendingOrderRequest,
    PositionModifyRequest,
    OrderModifyRequest,
    SeekRequest,
    AdvanceRequest,
    WhatIfActionRequest,
    WhatIfRequest,
)
from .strategy_registry import (
    StrategyRegistryError,
    get_strategy_class,
    list_strategy_names,
    register_strategy,
    registered_strategies,
)

__all__ = [
    "SessionCoordinator",
    "SimulatorSessionManager",
    "SessionMetadata",
    "SessionRuntimeStore",
    "SQLiteSessionRuntimeStore",
    "AccountConfig",
    "DataConfig",
    "ExecutionConfig",
    "PositionSizeConfig",
    "ReportingConfig",
    "SimulationConfig",
    "SimulationConfigError",
    "StrategyConfig",
    "SimulationStartRequest",
    "SimulationUpdateRequest",
    "ManualTradeRequest",
    "PendingOrderRequest",
    "PositionModifyRequest",
    "OrderModifyRequest",
    "SeekRequest",
    "AdvanceRequest",
    "WhatIfActionRequest",
    "WhatIfRequest",
    "StrategyRegistryError",
    "get_strategy_class",
    "list_strategy_names",
    "register_strategy",
    "registered_strategies",
]
