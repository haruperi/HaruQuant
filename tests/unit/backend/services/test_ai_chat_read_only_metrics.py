from __future__ import annotations

from backend.tools.read_only.backtests import BacktestSummaryTool
from backend.tools.read_only.optimization import OptimizationResultsTool
from backend.tools.read_only.portfolio import PortfolioSummaryTool, RiskSnapshotTool


class StubDb:
    def get_backtest_run(self, backtest_id: int):
        return {"status": "completed", "strategy_id": 17, "total_trades": 42, "symbols": ["SPY"], "timeframes": ["1D"]}

    def get_backtest_finance_metrics(self, backtest_id: int):
        return {
            "trade_metrics": {"profit_factor": 1.8, "win_rate": 57.0},
            "return_metrics": {"net_profit": 1250.0, "cagr": 18.4, "sharpe_ratio": 1.35},
            "drawdown_metrics": {"max_drawdown": 7.2},
        }

    def get_optimization_run(self, optimization_id: int):
        return {"status": "completed", "strategy_id": 17, "best_score": 2.4, "best_parameters": {"fast": 10}}

    def get_optimization_results(self, optimization_id: int, limit: int = 5):
        return [
            {"rank": 1, "score": 2.4, "sharpe_ratio": 1.5, "profit_factor": 1.9, "max_drawdown": 6.0},
            {"rank": 2, "score": 2.1, "sharpe_ratio": 1.4, "profit_factor": 1.8, "max_drawdown": 6.8},
        ]

    def get_user_live_sessions(self, user_id: int):
        return [{"session_id": 1, "status": "running"}]

    def get_session_positions(self, session_id: int):
        return [
            {"symbol": "SPY", "size": 2.0, "current_profit": 150.0, "position_type": "long", "status": "open"},
            {"symbol": "QQQ", "size": 1.0, "current_profit": -40.0, "position_type": "long", "status": "open"},
        ]


def test_backtest_summary_tool_exposes_headline_metrics() -> None:
    payload = BacktestSummaryTool(StubDb()).run(user_id=1, context={"backtest_id": 7})

    assert payload["headline_metrics"]["net_profit"] == 1250.0
    assert payload["headline_metrics"]["cagr"] == 18.4
    assert payload["headline_metrics"]["sharpe_ratio"] == 1.35
    assert payload["headline_metrics"]["max_drawdown"] == 7.2


def test_optimization_results_tool_exposes_score_gap_metrics() -> None:
    payload = OptimizationResultsTool(StubDb()).run(user_id=1, context={"optimization_id": 9})

    assert payload["headline_metrics"]["best_score"] == 2.4
    assert payload["headline_metrics"]["best_sharpe_ratio"] == 1.5
    assert payload["headline_metrics"]["score_gap_to_runner_up"] == 0.3


def test_portfolio_and_risk_tools_expose_headline_metrics() -> None:
    portfolio_payload = PortfolioSummaryTool(StubDb()).run(user_id=1, context={})
    risk_payload = RiskSnapshotTool(StubDb()).run(user_id=1, context={})

    assert portfolio_payload["headline_metrics"]["aggregate_open_profit"] == 110.0
    assert portfolio_payload["headline_metrics"]["profitable_positions"] == 1
    assert risk_payload["headline_metrics"]["largest_exposure"] == 2.0
    assert risk_payload["headline_metrics"]["concentration_ratio"] > 0.6
