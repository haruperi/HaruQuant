import pandas as pd

from services.simulation.config import SimulationConfig
from services.simulation.data_preparation import PreparedSimulationData
from services.simulation.position_sizing import resolve_position_size


def _prepared():
    return PreparedSimulationData(
        ticks=pd.DataFrame(
            {
                "bid": [1.1000, 1.1010, 1.1020],
                "ask": [1.1002, 1.1012, 1.1022],
                "symbol": ["AUDUSD", "AUDUSD", "AUDUSD"],
                "entry_signal": [1, 0, 0],
                "sl": [1.0902, 0.0, 0.0],
            },
            index=pd.to_datetime(
                [
                    "2025-01-01 00:00:00",
                    "2025-01-01 00:30:00",
                    "2025-01-01 01:00:00",
                ]
            ),
        )
    )


def _config(position_size):
    return SimulationConfig.from_dict(
        {
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
                "position_size": position_size,
            },
        }
    )


def test_resolve_fixed_lot_position_size():
    size = resolve_position_size(
        _config({"type": "fixed_lot", "lot_size": 0.23}),
        _prepared(),
    )

    assert size == 0.23


def test_resolve_fixed_percent_position_size():
    size = resolve_position_size(
        _config(
            {
                "type": "fixed_percent",
                "risk_percent": 1.0,
                "use_dynamic_stop_loss": False,
            }
        ),
        _prepared(),
    )

    assert size == 0.1


def test_resolve_milestone_position_size():
    config = _config(
        {
            "type": "milestone",
            "initial_balance": 10000.0,
            "base_lot_size": 0.1,
            "milestone_amount": 3000.0,
            "lot_increment": 0.1,
        }
    )
    config = SimulationConfig.from_dict(
        {
            **{
                "engine_type": config.engine_type,
                "account": {"initial_balance": 16000.0},
                "data": {
                    "source": config.data.source,
                    "symbols": list(config.data.symbols),
                    "timeframe": config.data.timeframe,
                    "start": config.data.start,
                    "end": config.data.end,
                    "warmup_start": config.data.warmup_start,
                },
                "strategy": {"name": config.strategy.name, "params": config.strategy.params},
                "execution": {
                    "tick_model": config.execution.tick_model,
                    "spread_model": config.execution.spread_model,
                    "contract_size": config.execution.contract_size,
                    "position_size": config.execution.position_size.params,
                },
            }
        }
    )

    size = resolve_position_size(config, _prepared())

    assert size == 0.3


def test_resolve_kelly_position_size():
    size = resolve_position_size(
        _config(
            {
                "type": "kelly_criterion",
                "kelly_fraction_limit": 0.25,
                "win_rate": 0.55,
                "avg_win": 150.0,
                "avg_loss": 100.0,
            }
        ),
        _prepared(),
    )

    assert size == 0.02


def test_resolve_volatility_adjusted_atr_position_size():
    size = resolve_position_size(
        _config(
            {
                "type": "volatility_adjusted_atr",
                "risk_percent": 1.0,
                "atr_multiplier": 2.0,
                "atr": 0.002,
            }
        ),
        _prepared(),
    )

    assert size == 0.25


def test_resolve_fixed_fractional_position_size():
    size = resolve_position_size(
        _config(
            {
                "type": "fixed_fractional",
                "fractional_factor": 0.5,
            }
        ),
        _prepared(),
    )

    assert size == 0.01
