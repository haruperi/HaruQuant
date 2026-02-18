# In-trade Controls (IP-28)

This page documents in-trade monitoring and circuit-breaker controls exposed from C++ via `hqt_engine._risk`.

## Components

- `IntradayRiskMonitor`
- `CircuitBreaker`
- `RiskState` (`NORMAL`, `PROTECTIVE`, `HALT`)

## Intraday Monitoring

`IntradayRiskMonitor` evaluates current state from:
- equity curve (drawdown)
- recent returns (volatility spike)
- optional HMM stress probability input (`evaluate_with_hmm`)

### Config

- `protective_drawdown_frac`
- `halt_drawdown_frac`
- `volatility_spike_mult`
- `halt_volatility_spike_mult`
- `volatility_window`
- `use_hmm_proxy`
- `hmm_stress_probability_threshold`

### Output Snapshot

- `state`
- `drawdown_breached`
- `volatility_spike`
- `drawdown_frac`
- `volatility_now`
- `volatility_baseline`
- `used_hmm_proxy`
- `hmm_stress_probability`
- `reason`

## Circuit Breakers

`CircuitBreaker` supports:
- global halt (`trip_global`, `reset_global`)
- strategy halt (`trip_strategy`, `reset_strategy`)
- trade gate decision (`can_trade(strategy_id)`)

### Policy Codes

- `OK`
- `STRATEGY_CIRCUIT_BREAKER`
- `GLOBAL_CIRCUIT_BREAKER`

## Example

```python
import hqt_engine

risk = hqt_engine._risk

monitor = risk.IntradayRiskMonitor(risk.IntradayRiskConfig())
snapshot = monitor.evaluate_with_hmm(
    equity_curve=[10000, 10020, 9950],
    returns_window=[0.001, 0.0011, 0.0009, 0.0012],
    hmm_stress_probability=0.8,
)
print(snapshot.state, snapshot.reason)

breaker = risk.CircuitBreaker()
breaker.trip_strategy("alpha", "strategy_drawdown_limit")
print(breaker.can_trade("alpha").policy_code)
```

## Executable Usage

- `tests/usage/risk/10_intraday_circuit_breaker.py`
