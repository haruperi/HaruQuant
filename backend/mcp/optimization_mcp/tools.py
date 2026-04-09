"""Optimization MCP tool adapters over legacy execution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from apps.optimization.execution import EngineOptimizationResult
from backend.mcp.mt5_mcp.models import MCPToolSpec


class OptimizationRunner(Protocol):
    """Minimal callable shape required by the optimization MCP wrapper."""

    def __call__(
        self,
        *,
        strategy_path: str,
        class_name: str,
        data: Any,
        symbol: str,
        params: dict[str, Any],
        initial_balance: float,
        engine_type: str = "vectorised",
        position_size: float = 0.1,
    ) -> EngineOptimizationResult: ...


@dataclass(frozen=True)
class OptimizationExecutionTools:
    """MCP-facing adapter for legacy optimization execution."""

    runner: OptimizationRunner

    def run_backtest_candidate(
        self,
        *,
        strategy_path: str,
        class_name: str,
        data: Any,
        symbol: str,
        params: dict[str, Any],
        initial_balance: float,
        engine_type: str = "vectorised",
        position_size: float = 0.1,
    ) -> dict[str, Any]:
        result = self.runner(
            strategy_path=strategy_path,
            class_name=class_name,
            data=data,
            symbol=symbol,
            params=params,
            initial_balance=initial_balance,
            engine_type=engine_type,
            position_size=position_size,
        )
        return {
            "symbol": symbol,
            "engine_type": engine_type,
            "summary": result.summary(),
            "trade_count": int(result.total_trades),
            "processed_ticks": int(result.processed_ticks),
        }


OPTIMIZATION_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("run_backtest_candidate", "read", "Run one legacy optimization candidate through the backtest engine."),
)


__all__ = [
    "OPTIMIZATION_TOOL_SPECS",
    "OptimizationExecutionTools",
]
