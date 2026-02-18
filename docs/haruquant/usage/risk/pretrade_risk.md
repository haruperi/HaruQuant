# Pre-trade Risk Policy (IP-27)

This page documents the C++ pre-trade policy engine exposed at `hqt_engine._risk`.

## Scope

Implemented checks:
- candidate size bounds
- margin availability gate
- max drawdown gate
- max gross exposure gate
- max net exposure gate
- mode-aware limits (`LIVE` vs `BACKTEST`)

## API

- `RiskGovernorConfig`
- `RiskAccountState`
- `RiskGovernor.can_trade(...)`
- `RiskGovernor.can_trade_with_mode(...)`
- `RiskMode.LIVE`, `RiskMode.BACKTEST`

## Policy Codes

- `OK`
- `SIZE_INVALID`
- `INSUFFICIENT_MARGIN`
- `MAX_DRAWDOWN`
- `MAX_GROSS_EXPOSURE`
- `MAX_NET_EXPOSURE`

## Example

```python
import hqt_engine

risk = hqt_engine._risk

cfg = risk.RiskGovernorConfig()
cfg.max_drawdown_frac = 0.10
cfg.max_gross_exposure = 2.0
cfg.max_net_exposure = 1.0
cfg.live_limit_multiplier = 0.90
cfg.backtest_limit_multiplier = 1.10
cfg.min_order_size = 0.05
cfg.max_order_size = 2.0
cfg.max_margin_utilization = 0.80

governor = risk.RiskGovernor(cfg)

state = risk.RiskAccountState()
state.equity = 9800.0
state.peak_equity = 10000.0
state.gross_exposure = 1.7
state.net_exposure = 0.7

decision = governor.can_trade_with_mode(
    state,
    candidate_size=0.1,
    candidate_gross_add=0.15,
    candidate_net_delta=0.10,
    margin_required=100.0,
    free_margin=1000.0,
    mode=risk.RiskMode.LIVE,
)

print(decision.allowed, decision.policy_code, decision.reason)
```

## Executable Usage

- `tests/usage/risk/09_cpp_risk_policy.py`
