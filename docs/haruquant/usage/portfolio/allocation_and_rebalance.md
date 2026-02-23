# Allocation and Rebalance Usage (IP-26)

## Scope
C++-first portfolio allocation/rebalance/exposure primitives exposed through `haruquant.sim`.

## APIs
- `sim.PortfolioAllocator.equal_weight(symbols, max_total_exposure)`
- `sim.PortfolioAllocator.risk_parity(symbol_volatility, max_total_exposure)`
- `sim.PortfolioAllocator.custom(raw_weights, max_total_exposure, normalize=True)`
- `sim.PortfolioAllocator.apply_exposure_constraints(target_allocations, symbol_to_strategy, symbol_to_asset, constraints)`
- `sim.RebalanceController(policy)` + `should_rebalance(...)`

## Example
```python
from haruquant import sim

alloc = sim.PortfolioAllocator.risk_parity(
    {"EURUSD": 0.01, "GBPUSD": 0.015, "XAUUSD": 0.03},
    max_total_exposure=1.0,
)

constraints = sim.ExposureConstraints()
constraints.max_total_exposure = 0.9
constraints.max_symbol_exposure = 0.5
constraints.max_strategy_exposure = {"trend": 0.7, "carry": 0.5}
constraints.max_asset_exposure = {"FX": 0.6, "METAL": 0.5}

constrained = sim.PortfolioAllocator.apply_exposure_constraints(
    alloc,
    {"EURUSD": "trend", "GBPUSD": "trend", "XAUUSD": "carry"},
    {"EURUSD": "FX", "GBPUSD": "FX", "XAUUSD": "METAL"},
    constraints,
)

policy = sim.RebalancePolicy()
policy.schedule_interval_msc = 60_000
policy.drift_threshold = 0.10

controller = sim.RebalanceController(policy)
if controller.should_rebalance(now_msc=120_000, current_allocations=constrained, target_allocations=alloc):
    controller.mark_rebalanced(120_000)
```

## Notes
- Designed for C++ execution paths; Python is orchestration only.
- Same primitives can be reused by live allocation/risk controllers.

## Runnable Example
- `tests/usage/portfolio/01_cpp_allocation_rebalance.py`
