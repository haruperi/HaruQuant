"""Drawdown and loss-limit risk service."""

from __future__ import annotations

from typing import Any


def drawdown_state(portfolio_snapshot: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "daily_loss": float(portfolio_snapshot.get("daily_loss", 0.0)),
        "weekly_loss": float(portfolio_snapshot.get("weekly_loss", 0.0)),
        "monthly_loss": float(portfolio_snapshot.get("monthly_loss", 0.0)),
        "portfolio_drawdown": float(portfolio_snapshot.get("drawdown", portfolio_snapshot.get("portfolio_drawdown", 0.0))),
        "strategy_drawdown": float(portfolio_snapshot.get("strategy_drawdown", 0.0)),
        "symbol_drawdown": float(portfolio_snapshot.get("symbol_drawdown", 0.0)),
        "consecutive_losses": int(portfolio_snapshot.get("consecutive_losses", 0)),
    }
    failures: list[str] = []
    if metrics["daily_loss"] >= float(thresholds["max_daily_loss_pct"]):
        failures.append("max_daily_loss")
    if metrics["weekly_loss"] >= float(thresholds["max_weekly_loss_pct"]):
        failures.append("max_weekly_loss")
    if metrics["monthly_loss"] >= float(thresholds["max_monthly_loss_pct"]):
        failures.append("max_monthly_loss")
    if metrics["portfolio_drawdown"] >= float(thresholds["max_portfolio_drawdown_pct"]):
        failures.append("max_portfolio_drawdown")
    if metrics["strategy_drawdown"] >= float(thresholds["max_strategy_drawdown_pct"]):
        failures.append("max_strategy_drawdown")
    if metrics["symbol_drawdown"] >= float(thresholds["max_symbol_drawdown_pct"]):
        failures.append("max_symbol_drawdown")
    if metrics["consecutive_losses"] >= int(thresholds["max_consecutive_losses"]):
        failures.append("max_consecutive_losses")
    critical = metrics["daily_loss"] >= float(thresholds["kill_switch_daily_loss_pct"]) or metrics["portfolio_drawdown"] >= float(thresholds["kill_switch_portfolio_drawdown_pct"])
    return {"metrics": metrics, "failures": failures, "critical": critical}
