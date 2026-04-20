"""Read-only backtest chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


def _extract_numeric_metric(container: dict[str, Any], candidates: tuple[str, ...]) -> float | int | None:
    for key in candidates:
        value = container.get(key)
        if isinstance(value, (int, float)):
            return value
    return None


def _build_backtest_headline_metrics(metrics: dict[str, Any]) -> dict[str, float | int]:
    trade_metrics = metrics.get("trade_metrics", {}) or {}
    return_metrics = metrics.get("return_metrics", {}) or {}
    drawdown_metrics = metrics.get("drawdown_metrics", {}) or {}
    headline: dict[str, float | int] = {}

    metric_map = {
        "net_profit": _extract_numeric_metric(return_metrics, ("net_profit", "total_return", "total_profit")),
        "cagr": _extract_numeric_metric(return_metrics, ("cagr", "CAGR", "annual_return")),
        "sharpe_ratio": _extract_numeric_metric(return_metrics, ("sharpe_ratio", "Sharpe Ratio", "annualized_sharpe_ratio")),
        "profit_factor": _extract_numeric_metric(trade_metrics, ("profit_factor", "Profit Factor")),
        "win_rate": _extract_numeric_metric(trade_metrics, ("win_rate", "Win Rate", "percent_profitable")),
        "max_drawdown": _extract_numeric_metric(drawdown_metrics, ("max_drawdown", "max_drawdown_pct", "Max Drawdown")),
    }
    for key, value in metric_map.items():
        if value is not None:
            headline[key] = value
    return headline


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
        headline_metrics = _build_backtest_headline_metrics(metrics)
        return {
            "backtest_found": True,
            "backtest_id": int(backtest_id),
            "status": run.get("status"),
            "strategy_id": run.get("strategy_id"),
            "total_trades": run.get("total_trades"),
            "symbols": run.get("symbols"),
            "timeframes": run.get("timeframes"),
            "headline_metrics": headline_metrics,
            "metrics": {
                "trade_metrics": metrics.get("trade_metrics", {}),
                "return_metrics": metrics.get("return_metrics", {}),
                "drawdown_metrics": metrics.get("drawdown_metrics", {}),
            },
        }
