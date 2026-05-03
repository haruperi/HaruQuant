"""Robustness Department facade over Monte Carlo and walk-forward services."""

ROBUSTNESS_DEPARTMENT = "robustness"
CANONICAL_SOURCES = (
    "backend.services.optimization.monte_carlo",
    "backend.services.optimization.walk_forward",
)

__all__ = ["ROBUSTNESS_DEPARTMENT", "CANONICAL_SOURCES"]
