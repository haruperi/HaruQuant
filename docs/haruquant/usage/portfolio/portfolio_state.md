# Portfolio State Usage (IP-25)

## Goal
Track canonical portfolio/account/position state in the C++ simulation layer with thread-safe updates.

## Python Bridge Example

```python
from haruquant import sim

state = sim.PortfolioState(10000.0, "USD")

state.upsert_position("trend_v1", "EURUSD", 0.5, 500.0, 20.0)
state.upsert_position("meanrev_v1", "EURUSD", -0.2, 200.0, -5.0)
state.upsert_position("meanrev_v1", "GBPUSD", 0.8, 700.0, 15.0)

state.apply_realized_pnl("trend_v1", "EURUSD", 50.0, commission=2.0, swap=0.0)

snapshot = state.account_snapshot()
print(snapshot.balance, snapshot.equity, snapshot.margin, snapshot.profit)

by_symbol = state.positions_by_symbol()
print(by_symbol["EURUSD"].net_volume)
```

## Notes
- `PortfolioState` is currently scoped to simulation/backtest (`haruquant.sim`).
- Supports concurrent updates across multiple strategy IDs and symbols.
- Account snapshot fields are normalized as:
  - `profit` = total unrealized PnL
  - `equity` = `balance + credit + profit`
  - `margin_free` = `equity - margin`
