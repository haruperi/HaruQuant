"""
Optimization Result Data Classes.

Contains result structures for optimization runs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

# from apps.backtest.result import BacktestResult
BacktestResult = Any


@dataclass
class OptimizationResult:
    """Result from parameter optimization."""

    parameters: Dict[str, Any]
    result: BacktestResult
    metrics: Dict[str, float]
    score: float
    rank: int = 0

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return f"OptimizationResult(score={self.score:.4f}, rank={self.rank}, params={self.parameters})"


@dataclass
class OptimizationSummary:
    """Summary of optimization run."""

    best_params: Dict[str, Any]
    best_score: float
    best_result: Optional[BacktestResult]
    all_results: List[OptimizationResult] = field(default_factory=list)
    total_combinations: int = 0
    completed: int = 0
    failed: int = 0
    duration_seconds: float = 0.0

    def get_top_n(self, n: int = 10) -> List[OptimizationResult]:
        """Get top N results by score."""
        sorted_results = sorted(self.all_results, key=lambda x: x.score, reverse=True)
        return sorted_results[:n]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame for analysis."""
        rows = []
        for opt_result in self.all_results:
            row = {
                **opt_result.parameters,
                **opt_result.metrics,
                "score": opt_result.score,
                "rank": opt_result.rank,
            }
            rows.append(row)
        return pd.DataFrame(rows)
