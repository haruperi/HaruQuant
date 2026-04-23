from io import StringIO
from contextlib import redirect_stdout

import pandas as pd

from backend.services.execution.core import EquityPoint, RunResult, TradeRecord
from backend.services.simulation.config import SimulationConfig
from backend.services.simulation.data_preparation import PreparedSimulationData
from backend.services.simulation.reporting import print_simulation_summary
from backend.services.simulation.results import SimulationRunResult


def _config():
    return SimulationConfig.from_dict(
        {
            "engine_type": "vectorized",
            "account": {"initial_balance": 10000.0},
            "data": {
                "source": "metatrader",
                "symbols": ["AUDUSD", "EURGBP"],
                "timeframe": "H1",
                "start": "2025-01-01",
                "end": "2025-01-02",
                "warmup_start": "2024-12-31",
            },
            "strategy": {"name": "FixtureSignalStrategy", "params": {}},
            "execution": {
                "tick_model": "timeframe_ticks",
                "spread_model": "native_spread",
                "contract_size": 100000,
                "position_size": {"type": "fixed_lot", "lot_size": 0.1},
            },
        }
    )


def test_standard_result_exposes_metrics_and_symbol_summary():
    run_result = RunResult(
        trades=[
            TradeRecord(symbol="AUDUSD", profit_loss=120.0),
            TradeRecord(symbol="EURGBP", profit_loss=-20.0),
        ],
        equity_curve=[EquityPoint(balance=10100.0, equity=10100.0)],
        processed_ticks=44,
        final_balance=10100.0,
        final_equity=10100.0,
    )
    prepared = PreparedSimulationData(
        ticks=pd.DataFrame({"bid": [1.0], "ask": [1.1]}),
        metadata={"tick_count": 44},
    )

    result = SimulationRunResult.from_run_result(_config(), prepared, run_result)

    assert result.total_profit == 100.0
    assert result.total_return == 0.01
    assert result.trade_count == 2
    assert result.symbol_summary["AUDUSD"] == {"trades": 1.0, "pnl": 120.0}
    assert result.symbol_summary["EURGBP"] == {"trades": 1.0, "pnl": -20.0}


def test_reporting_consumes_standard_result_only():
    result = SimulationRunResult.from_run_result(
        _config(),
        PreparedSimulationData(ticks=pd.DataFrame({"bid": [1.0], "ask": [1.1]})),
        RunResult(
            trades=[TradeRecord(symbol="AUDUSD", profit_loss=50.0)],
            equity_curve=[],
            processed_ticks=4,
            final_balance=10050.0,
            final_equity=10050.0,
        ),
    )
    output = StringIO()

    with redirect_stdout(output):
        print_simulation_summary(result)

    text = output.getvalue()
    assert "processed_ticks=4" in text
    assert "total_profit=50.00" in text
    assert "portfolio_summary[AUDUSD]" in text
