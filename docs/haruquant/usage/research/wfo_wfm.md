# WFO/WFM and Replay Certification (IP-40)

IP-40 is implemented on the C++ side and exposed through `hqt_engine.sim`.

## C++ Components

- Replay certification:
  - `hqt::sim::ReplayTradeEvent`
  - `hqt::sim::ReplayCertifier`
- WFO/WFM orchestration:
  - `hqt::sim::WfoSpec`
  - `hqt::sim::WfoWfmOrchestrator`
  - `hqt::sim::EdgeDetector`

## Python Bridge Example

```python
from hqt_engine import sim

# Replay certification
baseline = []
e1 = sim.ReplayTradeEvent()
e1.time_msc = 1000
e1.symbol = "EURUSD"
e1.side = "BUY"
e1.price = 1.1000
e1.volume = 0.10
e1.ticket = 1
baseline.append(e1)

candidate = [e1]
cert = sim.ReplayCertifier.compare(baseline, candidate)
print(cert.consistent, cert.message)

# WFO windows
spec = sim.WfoSpec()
spec.train_bars = 252
spec.test_bars = 63
spec.step_bars = 63
windows = sim.WfoWfmOrchestrator.build_windows(1000, spec)
print("windows:", len(windows))
```

## Validation Evidence

- `cpp/tests/test_replay_certification.cpp`
- `cpp/tests/test_wfo_wfm.cpp`
