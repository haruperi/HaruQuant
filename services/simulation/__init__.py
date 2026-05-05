"""Simulation service for HaruQuant."""

from __future__ import annotations

__version__ = "1.0.0"

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
    "PreparedSimulationData",
    "SimulationDataPreparationError",
    "SimulationDataPreparer",
    "SimulationPositionSizingError",
    "SimulationSymbolInfo",
    "resolve_position_size",
    "SimulationRun",
    "SimulationRunResult",
    "print_portfolio_symbol_summary",
    "print_run_result_summary",
    "print_simulation_summary",
    "simulation_summary_rows",
    "SimulationRunner",
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

_EXPORT_MODULES = {
    "SessionCoordinator": "session_coordinator",
    "SimulatorSessionManager": "session_manager",
    "SessionMetadata": "session_backend",
    "SessionRuntimeStore": "session_backend",
    "SQLiteSessionRuntimeStore": "session_backend",
    "AccountConfig": "config",
    "DataConfig": "config",
    "ExecutionConfig": "config",
    "PositionSizeConfig": "config",
    "ReportingConfig": "config",
    "SimulationConfig": "config",
    "SimulationConfigError": "config",
    "StrategyConfig": "config",
    "PreparedSimulationData": "data_preparation",
    "SimulationDataPreparationError": "data_preparation",
    "SimulationDataPreparer": "data_preparation",
    "SimulationPositionSizingError": "position_sizing",
    "SimulationSymbolInfo": "position_sizing",
    "resolve_position_size": "position_sizing",
    "SimulationRun": "results",
    "SimulationRunResult": "results",
    "print_portfolio_symbol_summary": "reporting",
    "print_run_result_summary": "reporting",
    "print_simulation_summary": "reporting",
    "simulation_summary_rows": "reporting",
    "SimulationRunner": "runner",
    "SimulationStartRequest": "models",
    "SimulationUpdateRequest": "models",
    "ManualTradeRequest": "models",
    "PendingOrderRequest": "models",
    "PositionModifyRequest": "models",
    "OrderModifyRequest": "models",
    "SeekRequest": "models",
    "AdvanceRequest": "models",
    "WhatIfActionRequest": "models",
    "WhatIfRequest": "models",
    "StrategyRegistryError": "strategy_registry",
    "get_strategy_class": "strategy_registry",
    "list_strategy_names": "strategy_registry",
    "register_strategy": "strategy_registry",
    "registered_strategies": "strategy_registry",
}


def __getattr__(name: str):
    """Load simulation symbols lazily to keep package imports lightweight."""
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
