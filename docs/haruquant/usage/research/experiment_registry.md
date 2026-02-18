# Experiment Registry (IP-41)

IP-41 is implemented in C++ and exposed through `hqt_engine.sim`.

## Available C++ APIs

- `ExperimentRecord`
- `ExperimentRegistry`
- `SymbolClassifier`
- `SeasonalPatternAnalyzer`

## Python Bridge Example

```python
from hqt_engine import sim

registry = sim.ExperimentRegistry()

rec = sim.ExperimentRecord()
rec.experiment_id = "exp-20260218-001"
rec.strategy = "trend_following"
rec.symbol = "EURUSD"
rec.timeframe = "M15"
rec.period_start_msc = 1700000000000
rec.period_end_msc = 1700600000000
rec.metadata = {"owner": "research", "tag": "baseline"}
registry.upsert(rec)

hits = registry.query("trend_following", "EURUSD", None, None)
print(len(hits))

cls = sim.SymbolClassifier.classify("BTCUSD", 0.45)
print(cls.asset_class, cls.volatility_regime)  # crypto extreme
```

## Seasonal Analysis Example

```python
from hqt_engine import sim

timestamps = [
    1700000000000,
    1700086400000,
    1700172800000,
]
returns = [0.01, -0.02, 0.015]
holiday_days = {1700086400 // 86400}

report = sim.SeasonalPatternAnalyzer.analyze(timestamps, returns, holiday_days)
print(report.day_of_week)
print(report.holiday_vs_non_holiday)
```

## Validation

- `cpp/tests/test_experiment_registry.cpp`
