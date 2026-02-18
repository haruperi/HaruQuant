"""Usage example: C++ allocation, exposure constraints, and rebalance policy via bridge."""

from __future__ import annotations

from pathlib import Path
import sys


def _load_sim_module():
    root = Path(__file__).resolve().parents[3]
    build_bridge = root / "build" / "bridge" / "Release"
    if build_bridge.exists():
        sys.path.insert(0, str(build_bridge))
    from hqt_engine import sim  # type: ignore

    return sim


def main() -> None:
    sim = _load_sim_module()

    print("1) Risk-parity target allocation")
    target = sim.PortfolioAllocator.risk_parity(
        {"EURUSD": 0.010, "GBPUSD": 0.015, "XAUUSD": 0.030},
        1.0,
    )
    print(dict(target))

    print("\n2) Apply exposure constraints")
    constraints = sim.ExposureConstraints()
    constraints.max_total_exposure = 0.90
    constraints.max_symbol_exposure = 0.50
    constraints.max_strategy_exposure = {"trend": 0.70, "carry": 0.40}
    constraints.max_asset_exposure = {"FX": 0.60, "METAL": 0.50}

    constrained = sim.PortfolioAllocator.apply_exposure_constraints(
        target,
        {"EURUSD": "trend", "GBPUSD": "trend", "XAUUSD": "carry"},
        {"EURUSD": "FX", "GBPUSD": "FX", "XAUUSD": "METAL"},
        constraints,
    )
    print(dict(constrained))
    print("total exposure:", round(sum(constrained.values()), 6))

    print("\n3) Scheduled + drift-triggered rebalance checks")
    policy = sim.RebalancePolicy()
    policy.schedule_interval_msc = 60_000
    policy.drift_threshold = 0.10
    controller = sim.RebalanceController(policy)

    current = {"EURUSD": 0.45, "GBPUSD": 0.30, "XAUUSD": 0.15}
    should_now = controller.should_rebalance(1_000, current, constrained)
    print("should_rebalance@t=1000:", should_now)
    if should_now:
        controller.mark_rebalanced(1_000)

    should_at_30s = controller.should_rebalance(30_000, current, constrained)
    print("should_rebalance@t=30000:", should_at_30s)

    drifted = {"EURUSD": 0.20, "GBPUSD": 0.55, "XAUUSD": 0.15}
    should_drift = controller.should_rebalance(31_000, drifted, constrained)
    print("should_rebalance@drift:", should_drift)

    should_time = controller.should_rebalance(62_000, current, constrained)
    print("should_rebalance@interval:", should_time)


if __name__ == "__main__":
    main()

