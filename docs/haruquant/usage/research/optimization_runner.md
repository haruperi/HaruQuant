# Optimization Runners (IP-42)

IP-42 optimization runners are implemented in C++ and exposed through `hqt_engine.sim`.

## Runners

- `sim.GridSearchRunner.run(space, evaluator, max_evals=0)`
- `sim.RandomSearchRunner.run(space, samples, seed, evaluator)`
- `sim.GeneticSearchRunner.run(space, population_size, generations, seed, evaluator, mutation_rate=0.15)`
- `sim.BayesianSearchRunner.run(space, iterations, seed, evaluator, random_warmup=5, exploration_weight=0.20)`
- `sim.DistributedOptimizationRunner.run(params_list, evaluator, policy)`

## Parameter Space

`space` is a dictionary:

```python
{
    "param_a": [1.0, 2.0, 3.0],
    "param_b": [10.0, 20.0],
}
```

Evaluator signature:

```python
def evaluator(params: dict[str, float]) -> float:
    ...
```

Each run returns a list of `OptimizationTrial` sorted by score descending.

## Distributed Worker Policy

`OptimizationWorkerPolicy` fields:

- `max_workers`
- `max_restarts`
- `task_timeout_ms`
- `heartbeat_ms`

Result includes `OptimizationWorkerHealth`:

- `submitted`
- `completed`
- `failed`
- `restarted`
- `timeout_restarts`

## Example

See `tests/usage/research/usage_optimization_runners.py`.
See `tests/usage/research/usage_distributed_optimization_runner.py`.

## Validation Evidence

- `cpp/tests/test_optimization_runners.cpp`
- `cpp/tests/test_distributed_optimization_runner.cpp`
- `tests/usage/research/usage_optimization_runners.py`
- `tests/usage/research/usage_distributed_optimization_runner.py`
