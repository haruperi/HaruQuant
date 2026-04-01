"""Thin read-only adapters over persisted backtest, optimization, and strategy artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.sqlite.backtests import BacktestManager
from apps.sqlite.optimization import OptimizationManager
from apps.sqlite.strategies import StrategyManager


class _BoundBacktestManager(BacktestManager):
    def __init__(self, db_path: Optional[str] = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "data" / "database" / "haruquant.db")


class _BoundOptimizationManager(OptimizationManager):
    def __init__(self, db_path: Optional[str] = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "data" / "database" / "haruquant.db")


class _BoundStrategyManager(StrategyManager):
    def __init__(self, db_path: Optional[str] = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "data" / "database" / "haruquant.db")


class BacktestTools:
    """Expose minimal read-only validation inputs for Strategy QA."""

    def __init__(
        self,
        *,
        backtests: Optional[BacktestManager] = None,
        optimizations: Optional[OptimizationManager] = None,
        strategies: Optional[StrategyManager] = None,
    ) -> None:
        self.backtests = backtests or _BoundBacktestManager()
        self.optimizations = optimizations or _BoundOptimizationManager()
        self.strategies = strategies or _BoundStrategyManager()

    def backtest_get_run(self, *, backtest_id: int) -> Optional[Dict[str, Any]]:
        """Return one persisted backtest run."""
        return self.backtests.get_backtest_run(int(backtest_id))

    def backtest_get_trades(self, *, backtest_id: int) -> List[Dict[str, Any]]:
        """Return persisted trades for one backtest."""
        return self.backtests.get_backtest_trades(int(backtest_id))

    def backtest_get_finance_metrics(self, *, backtest_id: int) -> Dict[str, Any]:
        """Return persisted finance metrics for one backtest."""
        return self.backtests.get_backtest_finance_metrics(int(backtest_id))

    def optimization_get_run(self, *, optimization_id: int) -> Optional[Dict[str, Any]]:
        """Return one optimization run."""
        return self.optimizations.get_optimization_run(int(optimization_id))

    def optimization_get_top_results(
        self,
        *,
        optimization_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return the top optimization candidates by score."""
        return self.optimizations.get_optimization_results(
            int(optimization_id),
            limit=int(limit),
            order_by="score",
            ascending=False,
        )

    def validation_get_wfo_summary(self, *, optimization_id: int) -> Optional[Dict[str, Any]]:
        """Return walk-forward summary statistics if present."""
        return self.optimizations.get_walk_forward_summary(int(optimization_id))

    def validation_get_monte_carlo_summary(
        self,
        *,
        simulation_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return stored Monte Carlo summary if present."""
        return self.optimizations.get_monte_carlo_simulation(int(simulation_id))

    def validation_get_manifest(self, *, strategy_version_id: int) -> Optional[Dict[str, Any]]:
        """Return strategy version data plus adjacent metadata.json when available."""
        version = self.strategies.get_strategy_version(int(strategy_version_id))
        if version is None:
            return None
        manifest = dict(version)
        file_path = manifest.get("file_path")
        if file_path:
            metadata_path = Path(str(file_path)).with_name("metadata.json")
            if metadata_path.exists():
                with metadata_path.open("r", encoding="utf-8") as handle:
                    manifest["file_metadata"] = json.load(handle)
        return manifest
