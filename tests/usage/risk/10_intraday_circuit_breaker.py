"""Usage example for in-trade monitoring and circuit breakers via hqt_engine._risk."""

from __future__ import annotations

import sys
from pathlib import Path


def _load_engine() -> None:
    build_dir = Path(__file__).resolve().parents[3] / "build" / "bridge" / "Release"
    if build_dir.exists():
        sys.path.insert(0, str(build_dir))


def main() -> None:
    _load_engine()
    import hqt_engine

    risk = hqt_engine._risk

    cfg = risk.IntradayRiskConfig()
    cfg.protective_drawdown_frac = 0.05
    cfg.halt_drawdown_frac = 0.10
    cfg.volatility_spike_mult = 2.0
    cfg.halt_volatility_spike_mult = 3.0
    cfg.use_hmm_proxy = True
    cfg.hmm_stress_probability_threshold = 0.70
    monitor = risk.IntradayRiskMonitor(cfg)

    snapshot = monitor.evaluate_with_hmm(
        equity_curve=[10000.0, 10050.0, 10020.0, 9900.0],
        returns_window=[0.0010, 0.0012, 0.0011, 0.0008, 0.0010, 0.0013],
        hmm_stress_probability=0.82,
    )
    print("risk_state:", snapshot.state, "reason:", snapshot.reason)

    breaker = risk.CircuitBreaker()
    print("can_trade(alpha):", breaker.can_trade("alpha").allowed)
    breaker.trip_strategy("alpha", "strategy_drawdown_limit")
    print("after strategy trip:", breaker.can_trade("alpha").policy_code)
    breaker.trip_global("market_stress_global_halt")
    print("after global trip:", breaker.can_trade("beta").policy_code)


if __name__ == "__main__":
    main()
