# Portfolio State Update Performance (IP-25)

## Scope
Baseline notes for `PortfolioState` update path in C++ simulation runtime.

## Hot Paths
- `upsert_position(strategy_id, symbol, net_volume, margin, unrealized_pnl)`
- `apply_realized_pnl(strategy_id, symbol, realized_pnl, commission, swap)`

## Current Status
- Functional baseline implemented.
- Micro-benchmark harness to be added in a follow-up performance pass when IP-26/IP-27 are integrated.

## Sanity Observation
- Updates are protected by a single mutex to guarantee consistency for concurrent strategy/symbol writes.
- This favors correctness and deterministic accounting over maximum write throughput for MVP scope.
