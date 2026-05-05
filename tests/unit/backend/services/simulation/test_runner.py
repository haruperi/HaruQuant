import pandas as pd

from services.execution.core import EquityPoint, RunResult, TradeRecord
from services.simulation.config import SimulationConfig
from services.simulation.data_preparation import PreparedSimulationData
from services.simulation.runner import SimulationRunner


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.last_run_prepared = None
        self._result = RunResult(
            trades=[TradeRecord(ticket=1, symbol="AUDUSD", profit_loss=25.0)],
            equity_curve=[EquityPoint(balance=10025.0, equity=10025.0)],
            processed_ticks=0,
            final_balance=10025.0,
            final_equity=10025.0,
        )

    def reset_runtime(self, account_config):
        self.calls.append(("reset_runtime", account_config))

    def run_prepared(self, prepared, config):
        self.calls.append(("run_prepared", prepared, config))
        self.last_run_prepared = (prepared, config)
        return len(prepared.ticks)

    def get_run_result(self, processed_ticks=0):
        self.calls.append(("get_run_result", processed_ticks))
        self._result.processed_ticks = processed_ticks
        return self._result


class FakePreparer:
    def __init__(self):
        self.calls = []
        self.ticks = pd.DataFrame(
            {
                "bid": [1.0, 1.1],
                "ask": [1.0002, 1.1002],
                "symbol": ["AUDUSD", "AUDUSD"],
                "is_bar_close": [False, True],
            },
            index=pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 01:00:00"]),
        )

    def prepare(self, config):
        self.calls.append(("prepare", config))
        return PreparedSimulationData(
            ticks=self.ticks,
            metadata={
                "tick_count": len(self.ticks),
                "tick_counts_by_symbol": {"AUDUSD": len(self.ticks)},
            },
        )


def _config_dict():
    return {
        "engine_type": "vectorized",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
        },
        "data": {
            "source": "metatrader",
            "symbols": ["AUDUSD"],
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


def test_runner_parses_config_resets_prepares_runs_and_returns_payload():
    engine = FakeEngine()
    preparer = FakePreparer()

    run = SimulationRunner(engine, data_preparer=preparer).run(_config_dict())

    assert isinstance(run.config, SimulationConfig)
    assert run.prepared.ticks is preparer.ticks
    assert run.processed_ticks == 2
    assert run.final_balance == 10025.0
    assert run.final_equity == 10025.0
    assert len(run.trades) == 1
    assert engine.calls[0][0] == "reset_runtime"
    assert preparer.calls[0][0] == "prepare"
    assert engine.calls[1][0] == "run_prepared"
    assert engine.calls[2] == ("get_run_result", 2)
    assert engine.calls[1][2] is run.config
    assert engine.last_run_prepared == (run.prepared, run.config)
    assert run.metadata["processed_ticks"] == 2
    assert run.metadata["trade_count"] == 1
    assert run.metadata["prepared"]["tick_count"] == 2


def test_runner_accepts_already_parsed_config():
    config = SimulationConfig.from_dict(_config_dict())
    engine = FakeEngine()
    preparer = FakePreparer()

    run = SimulationRunner(engine, data_preparer=preparer).run(config)

    assert run.config is config
    assert engine.calls[0][1] is config.account
    assert preparer.calls[0][1] is config
