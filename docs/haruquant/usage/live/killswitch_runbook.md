# Kill-Switch Runbook (IP-29)

This runbook documents emergency trading controls exposed by `hqt_engine._risk.KillSwitchController`.

## States

- `NORMAL`: trading allowed
- `REDUCE_ONLY`: no new trades; reduce exposure only
- `HALT`: trading blocked
- `EMERGENCY_SHUTDOWN`: hard stop, trigger source recorded

## Core Operations

- `set_reduce_only(reason)`
- `trigger_strategy_kill_switch(strategy_id, reason)`
- `trigger_global_kill_switch(reason)`
- `request_emergency_shutdown(source, reason)` where `source` is usually `UI` or `API`
- `can_trade(strategy_id)` for gate decision
- `state_snapshot()` for state/trace visibility

## Typical Incident Flow

1. Set reduce-only during elevated risk.
2. If strategy-level breach occurs, trip strategy kill switch.
3. If market/system-wide breach occurs, trip global kill switch.
4. If immediate full stop is required, call emergency shutdown from UI/API.

## Example

```python
import hqt_engine

risk = hqt_engine._risk
ks = risk.KillSwitchController()

ks.set_reduce_only("risk_reduction_mode")
ks.trigger_global_kill_switch("global_risk_limit")
ks.request_emergency_shutdown("UI", "operator_emergency_stop")

decision = ks.can_trade("alpha")
print(decision.allowed, decision.policy_code, decision.source)
```

## Executable Usage

- `tests/usage/risk/11_killswitch_state_machine.py`
