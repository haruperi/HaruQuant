"""Read-only strategy chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.strategy.catalog import StrategyCatalogService


class StrategyParametersTool:
    name = "strategy_parameters"

    def __init__(self, db_manager: DatabaseManager, catalog_service: StrategyCatalogService) -> None:
        self.db = db_manager
        self.catalog = catalog_service

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        strategy_id = context.get("strategy_id")
        if strategy_id is None:
            return {"strategy_found": False}
        strategy = self.catalog.get_strategy(int(strategy_id), user_id=user_id)
        active_version_id = strategy.get("active_version_id")
        version = self.db.get_strategy_version(int(active_version_id)) if active_version_id else None
        return {
            "strategy_found": True,
            "strategy_id": int(strategy_id),
            "name": strategy.get("name"),
            "category": strategy.get("category"),
            "active_version": strategy.get("active_version"),
            "parameters": (version or {}).get("parameters") or {},
        }
