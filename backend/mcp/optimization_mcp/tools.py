"""Optimization MCP tool adapters over legacy execution and research helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from haruquant.utils import logger
from haruquant.research import UnsupervisedResearchService
from haruquant.optimization import EngineOptimizationResult
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


@dataclass(frozen=True)
class OptimizationResearchTools:
    """MCP-facing adapter for reusable unsupervised analysis."""

    service: UnsupervisedResearchService

    def analyze_unsupervised_market_structure(
        self,
        *,
        data: Any,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if config is None:
            result = self.service.analyze_frame(data)
        else:
            from haruquant.research import UnsupervisedResearchConfig

            clean_config = {key: value for key, value in config.items() if key != "enabled"}
            result = self.service.analyze_frame(
                data,
                config=UnsupervisedResearchConfig(**clean_config),
            )
        return result.to_metadata()


OPTIMIZATION_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("run_backtest_candidate", "read", "Run one legacy optimization candidate through the backtest engine."),
    MCPToolSpec("analyze_unsupervised_market_structure", "read", "Run reusable unsupervised market-structure analysis over feature-ready market data."),
)


__all__ = [
    "OPTIMIZATION_TOOL_SPECS",
    "OptimizationExecutionTools",
    "OptimizationResearchTools",
]
