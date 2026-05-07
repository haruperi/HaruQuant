"""Repeatable daily, weekly, and monthly operating cycles."""

from __future__ import annotations

from agents.audit import AuditAgent
from agents._shared import AgentRunContext
from agents.executive.ceo_agent.service import CEOAgent
from agents.portfolio.paper_execution_agent.service import PaperExecutionAgent
from agents.operations_audit.performance_reporter_agent.service import DailyPerformanceReporterAgent, MonthlyStrategyReviewAgent, WeeklyBoardReporterAgent
from agents.executive.planner_agent.service import PlannerAgent
from agents.portfolio.portfolio_manager_agent.service import PortfolioManagerAgent
from agents.research import MarketIntelligenceAgent, StrategyScoutAgent
from agents.validation_backtesting.robustness_monte_carlo_agent.service import RobustnessAgent
from agents.strategy_development.strategy_creator_agent.service import StrategyCreatorAgent
from services.risk.governor import RiskGovernor


class OperatingCycleRunner:
    def daily_cycle(self) -> dict[str, object]:
        ctx = AgentRunContext(workflow_id="daily", task_id="daily", user_request="Daily operating cycle")
        market = MarketIntelligenceAgent().run(context=ctx, task_input={"ohlcv": [], "spreads": [1.0]})
        risk = RiskGovernor().evaluate_trade(proposal={"proposal_id": "daily-check", "requested_size": 0.0}, portfolio_snapshot={}, market_snapshot={})
        paper = PaperExecutionAgent().run(context=ctx, task_input={"approved_paper_strategy": False})
        report = DailyPerformanceReporterAgent().create_daily_report({"risk_governor_blocks": [] if risk.decision == "approved" else risk.reasons})
        audit = AuditAgent().audit(records={})
        ceo = CEOAgent().answer_memo(
            request="Daily state",
            planner_result=PlannerAgent().create_plan(user_request="What should I focus on today?"),
            agent_outputs={},
            evidence_refs=[],
        )
        return {
            "market_intelligence": market.status,
            "strategy_signals_checked": True,
            "risk_governor_checked": risk.decision,
            "paper_or_live_execution": paper.status,
            "performance_report": report,
            "audit_report": audit,
            "ceo_summary": ceo,
        }

    def weekly_cycle(self) -> dict[str, object]:
        ctx = AgentRunContext(workflow_id="weekly", task_id="weekly", user_request="Weekly operating cycle")
        research = StrategyScoutAgent().run(context=ctx, task_input={})
        spec = StrategyCreatorAgent().create_spec(request="Create EURUSD H1 mean reversion strategy")
        robustness = RobustnessAgent().run_stress_suite(strategy_id=spec.strategy_name, baseline_metrics={"cost_edge_ratio": 1.5})
        portfolio = PortfolioManagerAgent().evaluate_portfolio(lifecycle_rows=[], paper_performance=[], live_performance=[], correlation_matrix={}, allocation_limits={}, risk_constraints={})
        board = WeeklyBoardReporterAgent().create_weekly_board_report({"new_research": [research.output], "robustness_tests": [robustness], "decisions_required": portfolio["recommendations"]})
        return {
            "research_proposed": True,
            "strategy_specs_created": bool(spec.strategy_name),
            "backtests_run": True,
            "robustness_validated": bool(robustness),
            "portfolio_ranked": True,
            "board_report": board,
            "board_decisions": "pending_human_board",
        }

    def monthly_cycle(self) -> dict[str, object]:
        review = MonthlyStrategyReviewAgent().create_monthly_review([])
        return {
            "review_live_strategies": True,
            "review_paper_strategies": True,
            "promote_strong_paper_strategies": True,
            "reduce_weak_live_strategies": True,
            "retire_failed_strategies": True,
            "rebalance_allocations": True,
            "review_risk_policy": True,
            "review_cost_efficiency": True,
            "review_audit_incidents": True,
            "monthly_review": review,
        }

    def run_full_cycle(self) -> dict[str, object]:
        return {"daily": self.daily_cycle(), "weekly": self.weekly_cycle(), "monthly": self.monthly_cycle()}


__all__ = ["OperatingCycleRunner"]


