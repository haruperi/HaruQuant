"""Read-only backtest chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


class BacktestSummaryTool:
    name = "backtest_summary"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        backtest_id = context.get("backtest_id")
        if backtest_id is None:
            return {"backtest_found": False}
        run = self.db.get_backtest_run(int(backtest_id))
        if not run:
            return {"backtest_found": False}
        metrics = self.db.get_backtest_finance_metrics(int(backtest_id))
        return {
            "backtest_found": True,
            "backtest_id": int(backtest_id),
            "status": run.get("status"),
            "strategy_id": run.get("strategy_id"),
            "total_trades": run.get("total_trades"),
            "symbols": run.get("symbols"),
            "timeframes": run.get("timeframes"),
            "metrics": {
                "trade_metrics": metrics.get("trade_metrics", {}),
                "return_metrics": metrics.get("return_metrics", {}),
                "drawdown_metrics": metrics.get("drawdown_metrics", {}),
            },
        }
