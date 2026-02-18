"""
Usage example for C++ distributed optimization runner.

Run:
    python tests/usage/research/usage_distributed_optimization_runner.py
"""

from __future__ import annotations

from hqt_engine import sim


def objective(params: dict[str, float]) -> float:
    x = params["x"]
    y = params["y"]
    return -((x - 2.0) ** 2) - ((y + 1.0) ** 2)


def main() -> None:
    params_list = [
        {"x": 0.0, "y": 0.0},
        {"x": 1.0, "y": -1.0},
        {"x": 2.0, "y": -1.0},
        {"x": 3.0, "y": 1.0},
    ]

    policy = sim.OptimizationWorkerPolicy()
    policy.max_workers = 2
    policy.max_restarts = 1
    policy.task_timeout_ms = 1000
    policy.heartbeat_ms = 10

    result = sim.DistributedOptimizationRunner.run(params_list, objective, policy)
    print("health:", result.health.submitted, result.health.completed, result.health.failed, result.health.restarted)
    if result.trials:
        print("best:", result.trials[0].score, result.trials[0].params)


if __name__ == "__main__":
    main()

