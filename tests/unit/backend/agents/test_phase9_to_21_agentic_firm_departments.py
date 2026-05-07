from __future__ import annotations

from agents.validation_backtesting.backtest_agent.service import BacktestAgent
from agents.validation_backtesting.backtest_agent.evaluator import BacktestAnalystAgent
from agents._shared import AgentRunContext
from agents.strategy_development.strategy_codegen_agent.service import CodegenAgent
from agents.validation_backtesting.optimization_comparator_agent.service import OptimizationAgent, OptimizationComparatorAgent
from agents.portfolio.paper_execution_agent.service import PaperExecutionAgent
from agents.operations_audit.performance_reporter_agent.service import DailyPerformanceReporterAgent, MonthlyStrategyReviewAgent, WeeklyBoardReporterAgent
from agents.portfolio.portfolio_manager_agent.service import PortfolioManagerAgent
from agents.risk.risk_reviewer_agent.service import RiskReviewerAgent
from agents.validation_backtesting.robustness_monte_carlo_agent.service import RobustnessAgent, RobustnessScorecard
from agents._shared.schemas import BacktestRequest, StrategySpec
from agents.validation_backtesting.statistical_validation_agent.service import StatisticalValidationAgent
from agents.strategy_development.strategy_creator_agent.service import StrategyCreatorAgent
from agents.strategy_development.strategy_reviewer_agent.service import StrategyReviewerAgent
from agents.strategy_development.strategy_reviewer_agent.tools import StrategySpecValidator
from execution.paper_broker import PaperBroker
from services.risk.governor import RiskGovernor


def _context() -> AgentRunContext:
    return AgentRunContext(workflow_id="wf", task_id="task", user_request="Create EURUSD H1 mean reversion strategy")


def _ohlcv(rows: int = 120) -> list[dict[str, float]]:
    price = 1.1
    data = []
    for index in range(rows):
        price += 0.0001 if index % 2 == 0 else -0.00005
        data.append({"open": price, "high": price + 0.0003, "low": price - 0.0003, "close": price})
    return data


def test_phase9_strategy_creation_validation_review_and_codegen() -> None:
    creator = StrategyCreatorAgent()
    spec = creator.create_spec(request="Create EURUSD H1 mean reversion strategy")

    assert spec.symbol == "EURUSD"
    assert spec.timeframe == "H1"
    assert StrategySpecValidator().validate(spec)["valid"] is True

    review = StrategyReviewerAgent().review(spec)
    assert review.verdict in {"approve", "needs_review"}

    code = CodegenAgent().generate_strategy_code(spec)
    assert "on_bar" in code["code"]
    assert code["code_hash"]


def test_phase12_and_13_backtest_package_and_diagnosis() -> None:
    request = BacktestRequest(
        strategy_id="strategy-eurusd-h1",
        symbol="EURUSD",
        timeframe="H1",
        config={"initial_balance": 100000, "commission": 0, "spread": 1.0, "slippage": 0.2, "execution_mode": "paper"},
    )

    package = BacktestAgent().run_backtest(request, ohlcv=_ohlcv())
    diagnosis = BacktestAnalystAgent().diagnose(package)

    assert package["metrics"]["trade_count"] >= 20
    assert "acceptance" in package
    assert diagnosis["deployment_recommendation"] in {"robustness_required", "revise_or_reject"}


def test_phase14_to_16_optimization_robustness_and_statistics() -> None:
    optimization = OptimizationAgent().run_sweep(strategy_id="strategy-1", grid={"lookback": [20, 40], "threshold": [1, 2]})
    comparison = OptimizationComparatorAgent().compare(optimization["runs"])
    robustness = RobustnessAgent().run_stress_suite(strategy_id="strategy-1", baseline_metrics={"cost_edge_ratio": 1.8})
    scorecard = RobustnessScorecard().score(robustness)
    stats = StatisticalValidationAgent().validate([0.001, -0.0004, 0.0012, 0.0003] * 30)

    assert comparison["recommended_candidate"]
    assert scorecard["decision"] in {"pass", "needs_review", "fail"}
    assert stats["evidence_quality_rating"] in {"weak", "moderate", "strong", "institutional_grade"}


def test_phase17_and_18_risk_governor_and_reviewer() -> None:
    governor = RiskGovernor()
    decision = governor.evaluate_trade(
        proposal={"proposal_id": "p1", "requested_size": 0.01, "expected_risk": {"amount": 100}},
        portfolio_snapshot={"equity": 100000, "open_positions": 1},
        market_snapshot={"spread": 1.0, "slippage": 0.2},
    )
    memo = RiskReviewerAgent().create_risk_memo(
        strategy_summary="EURUSD H1",
        evidence_reviewed=["bt-1"],
        risk_governor_output=decision,
    )

    assert decision.decision == "approved"
    assert decision.signature
    assert memo["key_risk_metrics"]["proposed_trade_risk"] <= 0.01


def test_phase19_paper_broker_and_paper_execution_agent() -> None:
    broker = PaperBroker()
    agent = PaperExecutionAgent(broker=broker)
    result = agent.run(
        context=_context(),
        task_input={
            "approved_paper_strategy": True,
            "trade_proposal": {
                "proposal_id": "paper-1",
                "symbol": "EURUSD",
                "side": "buy",
                "entry_type": "market",
                "requested_size": 0.01,
                "price": 1.1,
                "expected_risk": {"amount": 50},
            },
            "market_snapshot": {"spread": 0.0001, "slippage": 0.0},
        },
    )

    assert result.status == "completed"
    assert broker.account_snapshot()["open_positions"] == 1
    assert agent.promotion_criteria(paper_stats={"trading_days": 30, "trade_count": 30, "max_drawdown": 0.03})["eligible"] is True


def test_phase20_and_21_reporting_and_portfolio_manager() -> None:
    daily = DailyPerformanceReporterAgent().create_daily_report({"daily_pnl": 100, "trade_count": 4})
    weekly = WeeklyBoardReporterAgent().create_weekly_board_report({"decisions_required": ["approve micro-live"]})
    monthly = MonthlyStrategyReviewAgent().create_monthly_review(
        [{"strategy_id": "s1", "state": "paper", "score": 0.82}, {"strategy_id": "s2", "state": "active", "score": 0.2}]
    )
    portfolio = PortfolioManagerAgent().evaluate_portfolio(
        lifecycle_rows=[{"strategy_id": "s1", "state": "paper"}],
        paper_performance=[{"strategy_id": "s1", "trading_days": 35, "score": 0.84}],
        live_performance=[],
        correlation_matrix={},
        allocation_limits={"max_strategy_allocation": 0.1},
        risk_constraints={"max_strategy_drawdown": 0.08},
    )

    assert daily["daily_pnl"] == 100
    assert weekly["decisions_required"] == ["approve micro-live"]
    assert monthly["promotion_candidates"]
    assert portfolio["recommendations"][0]["decision_type"] == "promote_to_micro_live"
    assert portfolio["board_required"] is True


