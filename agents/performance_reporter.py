"""Performance Reporter Agent."""

from __future__ import annotations

from typing import Any

from agents._persistence import utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult


class DailyPerformanceReporterAgent:
    agent_name = "performance_reporter"

    def create_daily_report(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "report_type": "daily",
            "daily_pnl": snapshot.get("daily_pnl", 0.0),
            "open_exposure": snapshot.get("open_exposure", 0.0),
            "drawdown": snapshot.get("drawdown", 0.0),
            "trade_count": snapshot.get("trade_count", 0),
            "strategy_health": snapshot.get("strategy_health", {}),
            "rejected_trades": snapshot.get("rejected_trades", []),
            "risk_governor_blocks": snapshot.get("risk_governor_blocks", []),
            "execution_anomalies": snapshot.get("execution_anomalies", []),
            "next_actions": snapshot.get("next_actions", ["Review risk blocks", "Check strategy health"]),
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        report = self.create_daily_report(task_input)
        uri = write_json_artifact("reports/daily", f"daily-{utc_stamp()}.json", report)
        return AgentRunResult(agent_name=self.agent_name, status="completed", output={**report, "report_uri": uri}, evidence_refs=[uri])


class WeeklyBoardReporterAgent:
    agent_name = "weekly_board_reporter"

    def create_weekly_board_report(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        report = {
            "report_type": "weekly_board",
            "portfolio_performance": snapshot.get("portfolio_performance", {}),
            "paper_strategies": snapshot.get("paper_strategies", []),
            "live_strategies": snapshot.get("live_strategies", []),
            "new_research": snapshot.get("new_research", []),
            "backtests": snapshot.get("backtests", []),
            "robustness_tests": snapshot.get("robustness_tests", []),
            "risk_events": snapshot.get("risk_events", []),
            "cost_usage": snapshot.get("cost_usage", {}),
            "decisions_required": snapshot.get("decisions_required", []),
        }
        uri = write_json_artifact("reports/board", f"weekly-board-{utc_stamp()}.json", report)
        return {**report, "report_uri": uri}


class MonthlyStrategyReviewAgent:
    agent_name = "monthly_strategy_reviewer"

    def create_monthly_review(self, strategies: list[dict[str, Any]]) -> dict[str, Any]:
        ranked = sorted(strategies, key=lambda item: item.get("score", 0.0), reverse=True)
        return {
            "report_type": "monthly_strategy_review",
            "ranked_active_strategies": [item for item in ranked if item.get("state") == "active"],
            "ranked_paper_strategies": [item for item in ranked if item.get("state") == "paper"],
            "underperformers": [item for item in strategies if item.get("score", 0.0) < 0.4],
            "promotion_candidates": [item for item in strategies if item.get("state") == "paper" and item.get("score", 0.0) >= 0.75],
            "retirement_candidates": [item for item in strategies if item.get("score", 0.0) < 0.25],
            "correlated_strategy_clusters": [],
            "allocation_recommendations": ["Keep live allocation changes Board-gated."],
        }


__all__ = ["DailyPerformanceReporterAgent", "MonthlyStrategyReviewAgent", "WeeklyBoardReporterAgent"]
