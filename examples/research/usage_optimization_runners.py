"""
Usage example for C++ optimization runners exposed via hqt_engine.sim.

Run:
    python tests/usage/research/usage_optimization_runners.py
"""

from __future__ import annotations

from hqt_engine import sim


def objective(params: dict[str, float]) -> float:
    x = params["x"]
    y = params["y"]
    return -((x - 2.0) ** 2) - ((y + 1.0) ** 2)


def print_top(label: str, trials: list) -> None:
    best = trials[0]
    print(f"{label}: best_score={best.score:.4f}, params={best.params}, trials={len(trials)}")


def main() -> None:
    space = {
        "x": [0.0, 1.0, 2.0, 3.0],
        "y": [-2.0, -1.0, 0.0, 1.0],
    }

    grid = sim.GridSearchRunner.run(space, objective)
    random = sim.RandomSearchRunner.run(space, 24, 42, objective)
    genetic = sim.GeneticSearchRunner.run(space, 12, 8, 123, objective, 0.15)
    bayesian = sim.BayesianSearchRunner.run(space, 20, 7, objective, 4, 0.30)

    print_top("grid", grid)
    print_top("random", random)
    print_top("genetic", genetic)
    print_top("bayesian", bayesian)


if __name__ == "__main__":
    main()

