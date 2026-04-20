"""Read-only optimization chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


class OptimizationResultsTool:
    name = "optimization_results"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        optimization_id = context.get("optimization_id")
        if optimization_id is None:
            return {"optimization_found": False}
        run = self.db.get_optimization_run(int(optimization_id))
        if not run:
            return {"optimization_found": False}
        results = self.db.get_optimization_results(int(optimization_id), limit=5)
        return {
            "optimization_found": True,
            "optimization_id": int(optimization_id),
            "status": run.get("status"),
            "strategy_id": run.get("strategy_id"),
            "best_score": run.get("best_score"),
            "best_parameters": run.get("best_parameters"),
            "top_results": [
                {
                    "rank": row.get("rank"),
                    "score": row.get("score"),
                    "sharpe_ratio": row.get("sharpe_ratio"),
                    "profit_factor": row.get("profit_factor"),
                    "max_drawdown": row.get("max_drawdown"),
                }
                for row in results
            ],
        }
