# Monte Carlo and Sensitivity (IP-43)

IP-43 is implemented in C++ and exposed via `hqt_engine.sim`.

## C++ APIs

- `sim.MonteCarloAnalyzer.simulate(...)`
- `sim.SensitivityAnalyzer.analyze(...)`

## Monte Carlo Modes

- `sim.MonteCarloMode.Shuffle`
- `sim.MonteCarloMode.Bootstrap`
- `sim.MonteCarloMode.Perturb`

## Outputs

- `MonteCarloSummary`: simulations, mean, stddev, p05, p50, p95, probability_positive
- `SensitivityReport`: evaluations, stability_score, normalized_sensitivity, points

## Example

See `tests/usage/research/usage_monte_carlo_sensitivity.py`.

## Validation Evidence

- `cpp/tests/test_monte_carlo_sensitivity.cpp`
- `tests/usage/research/usage_monte_carlo_sensitivity.py`

