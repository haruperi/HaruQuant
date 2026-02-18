"""
Usage example for C++ Monte Carlo and sensitivity analysis (IP-43).
"""

from __future__ import annotations

from hqt_engine import sim


def objective(params: dict[str, float]) -> float:
    x = params["x"]
    y = params["y"]
    return -((x - 2.0) ** 2) - ((y + 1.0) ** 2)


def main() -> None:
    pnl = [1.0, -0.5, 0.3, 0.2, -0.1, 0.7]
    mc = sim.MonteCarloAnalyzer.simulate(
        pnl_series=pnl,
        simulations=500,
        seed=42,
        mode=sim.MonteCarloMode.Bootstrap,
        perturb_scale=0.10,
    )
    print("MC:", mc.simulations, mc.mean, mc.p05, mc.p50, mc.p95, mc.probability_positive)

    space = {
        "x": [0.0, 1.0, 2.0, 3.0],
        "y": [-2.0, -1.0, 0.0],
    }
    report = sim.SensitivityAnalyzer.analyze(space, objective, 0)
    print("Sensitivity evaluations:", report.evaluations)
    print("Stability score:", report.stability_score)
    print("Normalized sensitivity:", report.normalized_sensitivity)


if __name__ == "__main__":
    main()

