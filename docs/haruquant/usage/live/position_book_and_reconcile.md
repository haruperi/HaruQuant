# Position Book and Reconciliation Hooks (IP-32)

## Scope

This document covers C++ `PositionBook` behavior exposed via `hqt_engine.sim`:

- position updates from fills and account snapshots
- Netting and Hedging modes
- reconciliation hook entry points (`periodic` and `reconnect`)

## Core API

- `sim.PositionBook(mode=sim.PositionMode.Netting)`
- `apply_fill(fill_event)`
- `apply_account_snapshot(account_info)`
- `snapshot_positions()`
- `snapshot_account()`
- `periodic_reconcile(broker_positions, broker_account)`
- `reconnect_reconcile(broker_positions, broker_account)`

## Netting vs Hedging

- `PositionMode.Netting`:
  - one net position per symbol
  - long and short fills offset into a single `net_volume`
- `PositionMode.Hedging`:
  - keeps separate legs (`legs_for_symbol(symbol)`)
  - aggregates long/short/net only for snapshots and reconciliation

## Example

```python
from hqt_engine import sim

book = sim.PositionBook(sim.PositionMode.Netting)
fill = sim.FillEvent()
fill.symbol = "EURUSD"
fill.is_buy = True
fill.volume = 1.0
fill.price = 1.1000
book.apply_fill(fill)

account = sim.AccountInfoData()
account.balance = 10000.0
account.equity = 10000.0
book.apply_account_snapshot(account)

report = book.periodic_reconcile(book.snapshot_positions(), book.snapshot_account())
print(report.ok, report.trigger, report.issues)
```

## Evidence

- C++ tests: `cpp/tests/test_position_book.cpp`
- Python integration: `tests/integration/test_reconcile_hooks.py`

