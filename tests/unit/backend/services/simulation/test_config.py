from datetime import datetime

import pytest

from backend.services.simulation.config import (
    SimulationConfig,
    SimulationConfigError,
)


def _valid_config():
    return {
        "engine_type": "vectorized",
        "account": {
            "initial_balance": 10000.0,
            "commission": 7.0,
            "leverage": 400,
        },
        "data": {
            "source": "metatrader",
            "symbols": ["AUDUSD", "EURGBP", "NZDCHF"],
            "timeframe": "H1",
            "start": "2025-01-01",
            "end": "2025-12-31",
            "warmup_start": "2024-10-01",
        },
        "strategy": {
            "name": "TrendFollowingStrategy",
            "params": {
                "fast_period": 20,
                "slow_period": 50,
                "filter_period": 200,
            },
        },
        "execution": {
            "tick_model": "timeframe_ticks",
            "spread_model": "native_spread",
            "slippage_model": "fixed",
            "slippage_points": 1,
            "contract_size": 100000,
            "position_size": {
                "type": "fixed_lot",
                "lot_size": 0.1,
            },
        },
        "reporting": {
            "print_summary": True,
            "save_to_db": False,
        },
    }


def test_simulation_config_parses_valid_example_config():
    config = SimulationConfig.from_dict(_valid_config())

    assert config.engine_type == "vectorized"
    assert config.account.initial_balance == 10000.0
    assert config.account.commission == 7.0
    assert config.data.symbols == ("AUDUSD", "EURGBP", "NZDCHF")
    assert config.data.timeframe == "H1"
    assert config.data.start == datetime(2025, 1, 1)
    assert config.strategy.name == "TrendFollowingStrategy"
    assert config.strategy.params["fast_period"] == 20
    assert config.execution.tick_model == "timeframe_ticks"
    assert config.execution.position_size.type == "fixed_lot"
    assert config.execution.position_size.lot_size == 0.1
    assert config.reporting.print_summary is True


def test_simulation_config_defaults_engine_and_reporting():
    raw = _valid_config()
    raw.pop("engine_type")
    raw.pop("reporting")

    config = SimulationConfig.from_dict(raw)

    assert config.engine_type == "vectorized"
    assert config.reporting.print_summary is False
    assert config.reporting.save_to_db is False


def test_simulation_config_parses_local_source_alias_and_files():
    raw = _valid_config()
    raw["data"]["source"] = "csv"
    raw["data"]["local_files"] = {"AUDUSD": {"bars": "audusd_h1.csv"}}

    config = SimulationConfig.from_dict(raw)

    assert config.data.source == "local"
    assert config.data.local_files["AUDUSD"]["bars"] == "audusd_h1.csv"


def test_simulation_config_requires_files_for_local_source():
    raw = _valid_config()
    raw["data"]["source"] = "local"

    with pytest.raises(SimulationConfigError, match="local_files"):
        SimulationConfig.from_dict(raw)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (("data", "symbols"), "data.symbols"),
        (("data", "timeframe"), "data.timeframe"),
        (("strategy", "name"), "strategy.name"),
        (("execution", "position_size"), "execution.position_size"),
    ],
)
def test_simulation_config_rejects_missing_required_fields(path, expected):
    raw = _valid_config()
    target = raw
    for key in path[:-1]:
        target = target[key]
    target.pop(path[-1])

    with pytest.raises(SimulationConfigError, match=expected):
        SimulationConfig.from_dict(raw)


def test_simulation_config_rejects_invalid_engine_type():
    raw = _valid_config()
    raw["engine_type"] = "slow"

    with pytest.raises(SimulationConfigError, match="engine_type"):
        SimulationConfig.from_dict(raw)


def test_simulation_config_rejects_invalid_date_order():
    raw = _valid_config()
    raw["data"]["warmup_start"] = "2025-02-01"
    raw["data"]["start"] = "2025-01-01"

    with pytest.raises(SimulationConfigError, match="warmup_start"):
        SimulationConfig.from_dict(raw)


def test_simulation_config_rejects_fixed_spread_without_points():
    raw = _valid_config()
    raw["execution"]["spread_model"] = "fixed_spread"

    with pytest.raises(SimulationConfigError, match="spread_points"):
        SimulationConfig.from_dict(raw)


def test_simulation_config_parses_dynamic_slippage_bounds():
    raw = _valid_config()
    raw["execution"]["slippage_model"] = "dynamic"
    raw["execution"].pop("slippage_points")
    raw["execution"]["slippage_min"] = 1
    raw["execution"]["slippage_max"] = 5

    config = SimulationConfig.from_dict(raw)

    assert config.execution.slippage_model == "dynamic"
    assert config.execution.slippage_min == 1.0
    assert config.execution.slippage_max == 5.0


def test_simulation_config_rejects_dynamic_slippage_without_bounds():
    raw = _valid_config()
    raw["execution"]["slippage_model"] = "dynamic"
    raw["execution"].pop("slippage_points")

    with pytest.raises(SimulationConfigError, match="slippage_min"):
        SimulationConfig.from_dict(raw)


def test_simulation_config_rejects_non_positive_fixed_lot():
    raw = _valid_config()
    raw["execution"]["position_size"]["lot_size"] = 0

    with pytest.raises(SimulationConfigError, match="lot_size"):
        SimulationConfig.from_dict(raw)
