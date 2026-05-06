"""Read-only HaruQuant state adapters for AI Chat."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any

from tools.read_only.contracts import ReadOnlyToolRequest, ReadOnlyToolResult


ReadOnlyTool = Callable[[ReadOnlyToolRequest], ReadOnlyToolResult]


def portfolio_summary(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    metrics = _visible_metrics(request.page_context)
    data = {
        key: value
        for key, value in {
            "account_login": _metric_value(metrics, "account login"),
            "account_server": _metric_value(metrics, "account server"),
            "account_name": _metric_value(metrics, "account name"),
            "current_equity": _metric_value(metrics, "current equity"),
            "current_balance": _metric_value(metrics, "current balance"),
        }.items()
        if value is not None
    }
    if data:
        return _result("portfolio_summary", data=data, summary="Portfolio/account summary from current page context.", sources=["page_context:visibleMetrics"])
    return _result("portfolio_summary", status="unavailable", summary="No portfolio summary is visible or stored in the current read-only sources.")


def open_positions(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    rows = _query_first_existing(
        tables=("core_broker_positions", "positions", "live_positions"),
        limit=request.limit,
    )
    if rows:
        return _result("open_positions", data={"positions": rows}, summary=f"Found {len(rows)} open position rows.", sources=["sqlite:positions"])
    return _result("open_positions", status="unavailable", summary="No open positions were available from read-only storage.")


def backtest_summary(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    rows = _query_first_existing(
        tables=("backtest_run_refs", "backtests", "backtest_results"),
        where=_id_where("backtest_id", request.backtest_id),
        limit=request.limit,
    )
    if rows:
        return _result("backtest_summary", data={"backtests": rows}, summary=f"Loaded {len(rows)} backtest summary row(s).", sources=["sqlite:backtests"])
    return _result("backtest_summary", status="unavailable", summary="No matching backtest summary was available from read-only storage.")


def strategy_parameters(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    rows = _query_first_existing(
        tables=("strategy_specs", "strategy_versions", "strategy_lifecycle"),
        where=_id_where("strategy_id", request.strategy_id),
        limit=request.limit,
    )
    if rows:
        return _result("strategy_parameters", data={"strategies": rows}, summary=f"Loaded {len(rows)} strategy row(s).", sources=["sqlite:strategy"])
    return _result("strategy_parameters", status="unavailable", summary="No strategy parameters were available from read-only storage.")


def optimization_results(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    rows = _query_first_existing(
        tables=("robustness_run_refs", "optimization_runs", "optimizations"),
        where=_id_where("optimization_id", request.optimization_id),
        limit=request.limit,
    )
    if rows:
        return _result("optimization_results", data={"optimizations": rows}, summary=f"Loaded {len(rows)} optimization result row(s).", sources=["sqlite:optimization"])
    return _result("optimization_results", status="unavailable", summary="No optimization results were available from read-only storage.")


def risk_snapshot(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    metrics = _visible_metrics(request.page_context)
    page_data = {
        metric.get("id") or metric.get("label"): metric.get("value")
        for metric in metrics
        if isinstance(metric, dict) and any(term in str(metric.get("label") or metric.get("id") or "").lower() for term in ("risk", "drawdown", "exposure", "equity", "balance"))
    }
    rows = _query_first_existing(
        tables=("risk_risk_decisions", "risk_risk_assessment_requests", "risk_review_refs"),
        limit=request.limit,
    )
    if page_data or rows:
        return _result(
            "risk_snapshot",
            data={"page_metrics": page_data, "risk_rows": rows},
            summary="Risk snapshot assembled from current page metrics and read-only risk tables.",
            sources=["page_context:visibleMetrics", "sqlite:risk"],
        )
    return _result("risk_snapshot", status="unavailable", summary="No risk snapshot was available from read-only sources.")


def alert_history(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    rows = _query_first_existing(
        tables=("core_incidents", "gov_kill_switch_events", "audit_log"),
        limit=request.limit,
    )
    if rows:
        return _result("alert_history", data={"alerts": rows}, summary=f"Loaded {len(rows)} alert/audit row(s).", sources=["sqlite:alerts"])
    return _result("alert_history", status="unavailable", summary="No alert history was available from read-only storage.")


def symbol_stats(request: ReadOnlyToolRequest) -> ReadOnlyToolResult:
    symbol = request.symbol or _symbol_from_context(request.page_context)
    metrics = _visible_metrics(request.page_context)
    data = {
        "symbol": symbol,
        "timeframe": _timeframe_from_context(request.page_context),
        "visible_metrics": metrics[:12],
    }
    if symbol or metrics:
        return _result("symbol_stats", data=data, summary="Symbol stats from current page context.", sources=["page_context"])
    return _result("symbol_stats", status="unavailable", summary="No symbol stats were available from current page context.")


READ_ONLY_TOOLS: dict[str, ReadOnlyTool] = {
    "portfolio_summary": portfolio_summary,
    "open_positions": open_positions,
    "backtest_summary": backtest_summary,
    "strategy_parameters": strategy_parameters,
    "optimization_results": optimization_results,
    "risk_snapshot": risk_snapshot,
    "alert_history": alert_history,
    "symbol_stats": symbol_stats,
}


def _result(
    tool_name: str,
    *,
    status: str = "success",
    data: dict[str, Any] | None = None,
    summary: str,
    sources: list[str] | None = None,
    started: float | None = None,
    error: str | None = None,
) -> ReadOnlyToolResult:
    return ReadOnlyToolResult(
        tool_name=tool_name,
        status=status,  # type: ignore[arg-type]
        data=data or {},
        summary=summary,
        sources=sources or [],
        latency_ms=int((time.perf_counter() - started) * 1000) if started else 0,
        error=error,
    )


def _db_path() -> Path:
    return Path(os.getenv("HARUQUANT_DB_PATH", "data/database/haruquant-dev.db"))


def _connect() -> sqlite3.Connection | None:
    path = _db_path()
    if not path.exists():
        fallback = Path("data/database/haruquant.db")
        path = fallback if fallback.exists() else path
    if not path.exists():
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _query_first_existing(
    *,
    tables: tuple[str, ...],
    where: tuple[str, object] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    conn = _connect()
    if conn is None:
        return []
    try:
        existing = {
            row["name"]
            for row in conn.execute("select name from sqlite_master where type='table'")
        }
        for table in tables:
            if table not in existing:
                continue
            columns = [row["name"] for row in conn.execute(f"pragma table_info({table})")]
            clause = ""
            params: list[object] = []
            if where and where[0] in columns and where[1] is not None:
                clause = f" where {where[0]} = ?"
                params.append(where[1])
            query = f"select * from {table}{clause} limit ?"
            params.append(max(1, min(limit, 50)))
            rows = [_json_safe(dict(row)) for row in conn.execute(query, params)]
            if rows:
                return rows
    finally:
        conn.close()
    return []


def _id_where(column: str, value: str | int | None) -> tuple[str, object] | None:
    return (column, value) if value is not None else None


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, bytes):
            safe[key] = value.decode("utf-8", errors="replace")
        elif isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
            try:
                safe[key] = json.loads(value)
            except json.JSONDecodeError:
                safe[key] = value
        else:
            safe[key] = value
    return safe


def _visible_metrics(page_context: dict[str, Any]) -> list[dict[str, Any]]:
    intelligence = dict(page_context.get("payload", {}).get("page_intelligence") or {})
    return [metric for metric in list(intelligence.get("visibleMetrics") or []) if isinstance(metric, dict)]


def _metric_value(metrics: list[dict[str, Any]], label: str) -> Any:
    for metric in metrics:
        metric_label = str(metric.get("label") or metric.get("id") or "").lower()
        if label in metric_label:
            return metric.get("value")
    return None


def _symbol_from_context(page_context: dict[str, Any]) -> str | None:
    for ref in list(page_context.get("entity_refs") or []):
        if isinstance(ref, dict) and ref.get("type") == "symbol":
            return str(ref.get("id"))
    return None


def _timeframe_from_context(page_context: dict[str, Any]) -> str | None:
    for ref in list(page_context.get("entity_refs") or []):
        if isinstance(ref, dict) and ref.get("type") == "timeframe":
            return str(ref.get("id"))
    return None


__all__ = ["READ_ONLY_TOOLS", "ReadOnlyTool", *READ_ONLY_TOOLS.keys()]
