"""
Optimization Module.

Parameter optimization, walk-forward analysis, and Monte Carlo simulation.

This module provides tools for:
- Grid search and random search optimization
- Walk-forward analysis for out-of-sample validation
- Monte Carlo simulation for robustness testing
- Parallel processing for faster optimization

Moved from apps.backtest to create a dedicated optimization module.
"""

# Parallel processing
# Monte Carlo simulation
from . import monte_carlo, parallel

# Optimization methods
from .methods import (
    bayesian_optimization,
    genetic_algorithm,
    grid_search,
    random_search,
)

# Result classes
from .result import OptimizationResult, OptimizationSummary

# Scoring functions
from .scoring import (
    calmar_score,
    custom_score,
    profit_factor_score,
    sharpe_score,
    sortino_score,
)

# Walk-forward analysis
from .walk_forward import print_optimization_report, walk_forward

__version__ = "1.0.0"

__all__ = [
    # Result classes
    "OptimizationResult",
    "OptimizationSummary",
    # Scoring functions
    "sharpe_score",
    "sortino_score",
    "calmar_score",
    "profit_factor_score",
    "custom_score",
    # Optimization methods
    "grid_search",
    "random_search",
    "bayesian_optimization",
    "genetic_algorithm",
    # Walk-forward
    "walk_forward",
    "print_optimization_report",
    # Monte Carlo
    "monte_carlo",
    # Parallel
    "parallel",
]
