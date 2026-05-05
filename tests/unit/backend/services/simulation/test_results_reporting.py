from io import StringIO
from contextlib import redirect_stdout

import pandas as pd

from services.execution.core import EquityPoint, RunResult, TradeRecord
from services.simulation.config import SimulationConfig
from services.simulation.data_preparation import PreparedSimulationData
from services.simulation.reporting import print_simulation_summary, simulation_summary_rows
from services.simulation.results import SimulationRunResult


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


def _config_with_reporting(**reporting_overrides):
    raw = {
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
        "reporting": reporting_overrides,
    }
    return SimulationConfig.from_dict(raw)


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
        PreparedSimulationData(
            ticks=pd.DataFrame({"bid": [1.0], "ask": [1.1]}),
            signal_bars_by_symbol={
                "AUDUSD": pd.DataFrame(
                    {"close": [1.0, 1.1]},
                    index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
                ),
                "EURGBP": pd.DataFrame(
                    {"close": [0.8, 0.85]},
                    index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
                ),
            },
        ),
        RunResult(
            trades=[
                TradeRecord(
                    symbol="AUDUSD",
                    type="buy",
                    profit_loss=50.0,
                    open_price=1.0,
                    close_price=1.1,
                    open_time=pd.Timestamp("2025-01-01"),
                    close_time=pd.Timestamp("2025-01-02"),
                )
            ],
            equity_curve=[
                EquityPoint(timestamp=pd.Timestamp("2025-01-01"), balance=10000.0, equity=10000.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-02"), balance=10050.0, equity=10050.0),
            ],
            processed_ticks=4,
            final_balance=10050.0,
            final_equity=10050.0,
        ),
    )
    output = StringIO()

    with redirect_stdout(output):
        print_simulation_summary(result)

    text = output.getvalue()
    assert "Start" in text
    assert "Equity Final [$]" in text
    assert "Buy & Hold Return [%]" in text
    assert "# Trades" in text
    assert "portfolio_summary[AUDUSD]" in text


def test_reporting_respects_first_symbol_benchmark_policy():
    result = SimulationRunResult.from_run_result(
        _config_with_reporting(benchmark_policy="first_symbol"),
        PreparedSimulationData(
            ticks=pd.DataFrame({"bid": [1.0], "ask": [1.1]}),
            signal_bars_by_symbol={
                "AUDUSD": pd.DataFrame(
                    {"close": [1.0, 1.05]},
                    index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
                ),
                "EURGBP": pd.DataFrame(
                    {"close": [1.0, 2.0]},
                    index=pd.to_datetime(["2025-01-01", "2025-01-02"]),
                ),
            },
        ),
        RunResult(
            trades=[],
            equity_curve=[
                EquityPoint(timestamp=pd.Timestamp("2025-01-01"), balance=10000.0, equity=10000.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-02"), balance=10100.0, equity=10100.0),
            ],
            processed_ticks=2,
            final_balance=10100.0,
            final_equity=10100.0,
        ),
    )

    output = StringIO()
    with redirect_stdout(output):
        print_simulation_summary(result)

    text = output.getvalue()
    assert "Buy & Hold Return [%]" in text
    assert "5.00000" in text


def test_reporting_drawdown_duration_uses_final_equity_per_timestamp():
    result = SimulationRunResult.from_run_result(
        _config(),
        PreparedSimulationData(ticks=pd.DataFrame({"bid": [1.0], "ask": [1.1]})),
        RunResult(
            trades=[],
            equity_curve=[
                EquityPoint(timestamp=pd.Timestamp("2025-01-01 00:00:00"), balance=10000.0, equity=10000.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-01 00:00:00"), balance=10000.0, equity=10020.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-01 01:00:00"), balance=9980.0, equity=9980.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-01 01:00:00"), balance=9950.0, equity=9950.0),
                EquityPoint(timestamp=pd.Timestamp("2025-01-01 02:00:00"), balance=10030.0, equity=10030.0),
            ],
            processed_ticks=5,
            final_balance=10030.0,
            final_equity=10030.0,
        ),
    )

    rows = dict(simulation_summary_rows(result))

    assert rows["Max. Drawdown Duration"] == "0 days 01:00:00"
    assert rows["Avg. Drawdown Duration"] == "0 days 01:00:00"
