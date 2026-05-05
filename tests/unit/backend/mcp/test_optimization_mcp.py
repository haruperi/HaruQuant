from __future__ import annotations

import pandas as pd

from haruquant.research import UnsupervisedResearchService
from haruquant.optimization import EngineOptimizationResult
from backend_retiring.mcp.optimization_mcp import (
    OPTIMIZATION_TOOL_SPECS,
    OptimizationExecutionTools,
    OptimizationMCPServer,
    OptimizationResearchTools,
    create_optimization_mcp_server,
)


def _fake_runner(**_: object) -> EngineOptimizationResult:
    return EngineOptimizationResult(
        trades=pd.DataFrame(),
        equity_curve=pd.Series([10000.0, 10150.0]),
        initial_balance=10000.0,
        final_balance=10150.0,
        processed_ticks=250,
        total_trades=4,
        win_rate=0.5,
        profit_factor=1.6,
        sharpe_ratio=1.2,
        sortino_ratio=1.4,
        calmar_ratio=0.8,
        total_return_pct=1.5,
        max_drawdown_pct=0.7,
    )


def test_optimization_mcp_server_starts_with_expected_tool_specs() -> None:
    server = create_optimization_mcp_server()

    assert isinstance(server, OptimizationMCPServer)
    assert server.name == "optimization_mcp"
    assert server.started is False
    assert server.list_tools() == OPTIMIZATION_TOOL_SPECS


def test_optimization_mcp_server_startup_marks_server_ready() -> None:
    server = create_optimization_mcp_server()

    result = server.startup()

    assert result is server
    assert server.started is True


def test_optimization_execution_tools_return_stable_summary_shape() -> None:
    tools = OptimizationExecutionTools(runner=_fake_runner)

    result = tools.run_backtest_candidate(
        strategy_path="strategy.py",
        class_name="Strategy",
        data=object(),
        symbol="EURUSD",
        params={"lookback": 20},
        initial_balance=10000.0,
    )

    assert result["symbol"] == "EURUSD"
    assert result["engine_type"] == "vectorised"
    assert result["trade_count"] == 4
    assert result["processed_ticks"] == 250
    assert result["summary"]["final_balance"] == 10150.0


def test_optimization_research_tools_return_unsupervised_metadata() -> None:
    index = pd.date_range("2025-01-01", periods=48, freq="h", tz="UTC")
    closes = pd.Series([1.10 + 0.0005 * idx for idx in range(48)], index=index)
    data = pd.DataFrame(
        {
            "open": closes.values,
            "high": (closes + 0.001).values,
            "low": (closes - 0.001).values,
            "close": closes.values,
            "volume": [100 + idx for idx in range(48)],
            "ema_20": closes.ewm(span=20, adjust=False).mean().values,
            "ema_50": closes.ewm(span=50, adjust=False).mean().values,
        },
        index=index,
    )
    tools = OptimizationResearchTools(service=UnsupervisedResearchService())

    result = tools.analyze_unsupervised_market_structure(data=data)

    assert result["status"] == "COMPLETED"
    assert result["report"]["pca"]["model"] == "pca"
    assert "cluster_count" in result["strategy_context"]
