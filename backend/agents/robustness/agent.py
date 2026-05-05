"""Robustness Department facade over Monte Carlo and walk-forward services."""

ROBUSTNESS_DEPARTMENT = "robustness"
CANONICAL_SOURCES = (
    "services.optimization.monte_carlo",
    "services.optimization.walk_forward",
)

__all__ = ["ROBUSTNESS_DEPARTMENT", "CANONICAL_SOURCES"]
