# Benchmark and Validation Tests

This directory contains comprehensive benchmarking and validation tests for the HaruQuant backtest engine.

## Directory Structure

```
tests/
├── benchmarks/
│   ├── fixtures.py                    # Shared test fixtures
│   ├── test_backtest_performance.py   # Performance benchmarks
│   └── test_memory_usage.py           # Memory profiling tests
└── validation/
    ├── test_accuracy.py               # Numerical accuracy tests
    └── test_engine_parity.py          # Engine consistency tests
```

## Running Benchmarks

### Performance Benchmarks

Run all performance benchmarks:
```bash
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only
```

Save baseline results:
```bash
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-save=baseline
```

Compare against baseline:
```bash
pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-compare=baseline
```

Note: 100K-bar benchmarks use a single-iteration pedantic run to keep total
runtime reasonable while still producing a baseline.

## Regression Focus

These benchmarks are intended to show that performance is improving or at least
not regressing. To validate that, save a baseline and compare against it using
`--benchmark-compare=baseline`. If you want CI to fail on regressions, use the
pytest-benchmark comparison options to enforce thresholds.

### Memory Usage Tests

Run memory profiling tests:
```bash
pytest tests/benchmarks/test_memory_usage.py -v -s
```

## Running Validation Tests

### Accuracy Validation

Run numerical accuracy tests:
```bash
pytest tests/validation/test_accuracy.py -v
```

First run will save reference results. Subsequent runs will validate against the reference.

### Engine Parity

Test that EventDrivenEngine and VectorizedEngine produce consistent results:
```bash
pytest tests/validation/test_engine_parity.py -v
```

## Benchmark Fixtures

The `fixtures.py` module provides standardized test data:

- `sample_data_1k` - 1,000 bars of random OHLCV data
- `sample_data_10k` - 10,000 bars
- `sample_data_100k` - 100,000 bars
- `sample_data_1m` - 1,000,000 bars
- `simple_strategy` - Simple MA crossover strategy
- `complex_strategy` - Multi-indicator strategy

## Performance Baselines

After running benchmarks, baseline results are saved in `.benchmarks/` directory.

### Expected Performance (Phase 1-4 Optimizations)

| Test | Target | Notes |
|------|--------|-------|
| EventDrivenEngine 1K bars | <100ms | With minimal config |
| EventDrivenEngine 10K bars | <2s | With minimal config |
| VectorizedEngine 100K bars | <1s | Fast vectorized execution |
| Memory per 100K bars | <500MB | EventDrivenEngine |

## Validation Criteria

### Numerical Accuracy
- Deterministic results (same inputs → same outputs)
- Results match saved reference (within 0.01% tolerance)
- Edge cases handled correctly

### Engine Parity
- Same trade count between engines
- Same final balance (within $1 tolerance)
- Same return percentage (within 0.1% tolerance)
- Same win rate (within 1% tolerance)

## Adding New Benchmarks

1. Add test function to appropriate test file
2. Use `benchmark` fixture from pytest-benchmark
3. Follow naming convention: `test_<engine>_<scenario>`
4. Document expected performance in this README

## Continuous Integration

Benchmarks should be run:
- Before major releases
- After significant optimizations
- When performance regressions are suspected

Validation tests should be run:
- On every commit (CI/CD)
- Before merging pull requests
- After any engine modifications
