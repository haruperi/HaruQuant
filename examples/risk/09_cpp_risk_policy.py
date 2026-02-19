"""Usage example for C++ risk policy bindings via hqt_engine._risk."""

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

    cfg = risk.RiskGovernorConfig()
    cfg.max_drawdown_frac = 0.10
    cfg.max_gross_exposure = 2.0
    cfg.max_net_exposure = 1.0
    governor = risk.RiskGovernor(cfg)

    state = risk.RiskAccountState()
    state.equity = 9800.0
    state.peak_equity = 10000.0
    state.gross_exposure = 1.4
    state.net_exposure = 0.6

    decision = governor.can_trade_with_mode(
        state,
        candidate_size=0.2,
        candidate_gross_add=0.4,
        candidate_net_delta=0.3,
        margin_required=120.0,
        free_margin=1000.0,
        mode=risk.RiskMode.LIVE,
    )
    print("can_trade:", decision.allowed, decision.policy_code, decision.reason)

    pref = risk.CorrelationPreference()
    pref.target_corr = 0.5
    pref.penalty_strength = 2.0
    allocator = risk.RiskBudgetAllocator(pref)

    target = allocator.compute_target_lots(
        base_lots={"EURUSD": 1.0, "GBPUSD": 1.0, "USDJPY": 0.5},
        budgets={"EURUSD": 0.4, "GBPUSD": 0.4, "USDJPY": 0.2},
        corr_map={"EURUSD": 0.9, "GBPUSD": 0.2, "USDJPY": 0.1},
    )
    deltas = allocator.lots_to_deltas(
        current={"EURUSD": 1.0, "GBPUSD": 1.0, "USDJPY": 0.5},
        target=target,
    )

    print("target_lots:", target)
    print("rebalance_deltas:", deltas)


if __name__ == "__main__":
    main()
