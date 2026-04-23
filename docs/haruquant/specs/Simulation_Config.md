# Simulation Config

`Engine.run(config)` is the public backtest entry point. The example layer should build a JSON-compatible config and let `backend.services.simulation` handle reset, data preparation, strategy instantiation, tick generation, simulation, and result packaging.

```python
config = {
    "engine_type": "vectorized",
    "account": {
        "initial_balance": 10000.0,
        "commission": 7.0,
        "leverage": 400,
        "currency": "USD",
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
        "params": {"fast_period": 20, "slow_period": 50, "filter_period": 200},
    },
    "execution": {
        "tick_model": "timeframe_ticks",
        "spread_model": "native_spread",
        "slippage_model": "fixed",
        "slippage_points": 1,
        "contract_size": 100000,
        "position_size": {"type": "fixed_lot", "lot_size": 0.1},
    },
}

result = engine.run(config)
```

Supported `data.source`: `metatrader`, `dukascopy`, `local`.

Supported `tick_model`: `timeframe_ticks`, `m1_ticks`, `real_ticks`, `synthetic_ticks`.

Supported `spread_model`: `native_spread`, `fixed_spread`, `variable_spread`.

Supported `slippage_model`: `none`, `fixed`, `dynamic`.

Supported `position_size.type`: `fixed_lot`, `fixed_percent`, `milestone`, `kelly_criterion`, `volatility_adjusted_atr`, `fixed_fractional`.

The simulator backends consume prepared ticks and primitive execution values. They must not load data, instantiate strategies, save to DB, or print reports.
