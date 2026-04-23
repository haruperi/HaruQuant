import pandas as pd

import backend.services.simulation.runner as runner_module
from backend.services.simulation.config import SimulationConfig
from backend.services.simulation.data_preparation import PreparedSimulationData
from backend.services.simulation.engine import Engine


def _config(engine_type="vectorized"):
    return SimulationConfig.from_dict(
        {
            "engine_type": engine_type,
            "account": {"initial_balance": 10000.0},
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
    )


def _prepared():
    return PreparedSimulationData(
        ticks=pd.DataFrame(
            {
                "bid": [1.0],
                "ask": [1.0002],
                "symbol": ["AUDUSD"],
                "is_bar_close": [True],
            },
            index=pd.to_datetime(["2025-01-01 00:00:00"]),
        )
    )


def test_engine_run_routes_config_to_simulation_runner(monkeypatch):
    calls = []

    class FakeRunner:
        def __init__(self, engine):
            calls.append(("init", engine))
            self.engine = engine

        def run(self, config):
            calls.append(("run", config))
            return {"result": "ok"}

    monkeypatch.setattr(runner_module, "SimulationRunner", FakeRunner)
    engine = Engine.__new__(Engine)
    config = _config()

    result = engine.run(config)

    assert result == {"result": "ok"}
    assert calls == [("init", engine), ("run", config)]


def test_engine_run_prepared_routes_vectorized_engine():
    engine = Engine.__new__(Engine)
    calls = []

    def fake_run_vectorized(
        data,
        initial_balance,
        contract_size,
        position_size,
        commission_per_lot,
        slippage_model,
        slippage_points,
        slippage_min,
        slippage_max,
    ):
        calls.append(
            (
                data,
                initial_balance,
                contract_size,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
            )
        )
        return len(data)

    engine.run_vectorized = fake_run_vectorized
    prepared = _prepared()
    config = _config("vectorized")

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert calls == [
        (prepared.ticks, 10000.0, 100000.0, 0.1, 0.0, "none", 0.0, None, None)
    ]


def test_engine_run_prepared_routes_event_driven_engine():
    engine = Engine.__new__(Engine)
    calls = []

    def fake_run_event_driven(
        data,
        position_size=None,
        commission_per_lot=0.0,
        slippage_model="none",
        slippage_points=0.0,
        slippage_min=None,
        slippage_max=None,
    ):
        calls.append(
            (
                data,
                position_size,
                commission_per_lot,
                slippage_model,
                slippage_points,
                slippage_min,
                slippage_max,
            )
        )
        return len(data)

    engine.run_event_driven = fake_run_event_driven
    prepared = _prepared()
    config = _config("event_driven")

    processed_ticks = engine.run_prepared(prepared, config)

    assert processed_ticks == 1
    assert calls == [(prepared.ticks, 0.1, 0.0, "none", 0.0, None, None)]
