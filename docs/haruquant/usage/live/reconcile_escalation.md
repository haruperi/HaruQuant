# Reconciliation Escalation and Blocking (IP-33)

## Scope

This guide covers mismatch escalation policy after reconciliation:

- mismatch severity and incident report generation
- policy split: `Auto` vs `Manual`
- blocking new orders on major or manual-controlled discrepancies

## Core API

- `report = PositionBook.periodic_reconcile(...)`
- `report = PositionBook.reconnect_reconcile(...)`
- `decision = PositionBook.evaluate_reconciliation(report, policy, major_threshold)`
- `PositionBook.write_incident_report(path, report, decision)`

## Policy Behavior

- `ReconcilePolicy.Auto`
  - clean report: allow new orders
  - minor mismatch: alert, can continue
  - major mismatch (>= `major_threshold`): block new orders, require manual resolution
- `ReconcilePolicy.Manual`
  - any mismatch blocks new orders until operator resolution

## Example

```python
from haruquant import sim

book = sim.PositionBook(sim.PositionMode.Netting)
report = book.reconnect_reconcile(broker_positions, broker_account)
decision = book.evaluate_reconciliation(report, sim.ReconcilePolicy.Auto, 2)

if decision.allow_new_orders:
    print("continue order flow")
else:
    print("SAFE_MODE: block new orders")

book.write_incident_report(
    "artifacts/logs/live/reconcile_discrepancy_report.json",
    report,
    decision,
)
```

## Evidence

- `cpp/tests/test_reconcile_escalation.cpp`
- `tests/e2e/test_reconcile_mismatch_blocking.py`
- `artifacts/logs/live/reconcile_discrepancy_report.json`

