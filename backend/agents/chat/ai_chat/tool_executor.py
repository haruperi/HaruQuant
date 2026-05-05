"""Read-only HaruQuant tool executor for AI chat grounding."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from services.utils.logger import logger
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.policies.tool_policy import ToolPolicy
from services.strategy.catalog import StrategyCatalogService
from backend.tools.read_only import (
    AlertHistoryTool,
    BacktestSummaryTool,
    LatestCandleTool,
    OpenPositionsTool,
    OptimizationResultsTool,
    PortfolioSummaryTool,
    RiskSnapshotTool,
    StrategyParametersTool,
    SymbolStatsTool,
    InternalKnowledgeTool,
)


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    payload: dict[str, Any]
    latency_ms: int
    success: bool
    error: str | None = None


class ToolExecutor:
    """Execute allowlisted read-only tools with lightweight retry and timing."""

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        policy: ToolPolicy | None = None,
    ) -> None:
        self.db = db_manager or DatabaseManager()
        self.policy = policy or ToolPolicy()
        catalog = StrategyCatalogService(db_manager=self.db)
        self._tools = {
            "portfolio_summary": PortfolioSummaryTool(self.db),
            "open_positions": OpenPositionsTool(self.db),
            "backtest_summary": BacktestSummaryTool(self.db),
            "strategy_parameters": StrategyParametersTool(self.db, catalog),
            "optimization_results": OptimizationResultsTool(self.db),
            "risk_snapshot": RiskSnapshotTool(self.db),
            "alert_history": AlertHistoryTool(self.db),
            "symbol_stats": SymbolStatsTool(self.db),
            "latest_candle": LatestCandleTool(self.db),
            "internal_knowledge": InternalKnowledgeTool(),
        }

    def execute(
        self,
        *,
        user_id: int,
        requested_tools: tuple[str, ...],
        context: dict[str, Any],
        authority_band: object = "read_only",
        permission_tier: object = "T1_READ_ONLY",
    ) -> tuple[list[ToolExecutionResult], tuple[str, ...]]:
        decision = self.policy.allow_tools(
            requested=requested_tools,
            authority_band=authority_band,
            permission_tier=permission_tier,
        )
        results: list[ToolExecutionResult] = []
        for tool_name in decision.allowed:
            start = perf_counter()
            try:
                tool = self._tools[tool_name]
                payload = self._run_with_retry(tool_name=tool_name, user_id=user_id, context=context)
                latency_ms = int((perf_counter() - start) * 1000)
                logger.info(f"AI chat tool executed: tool={tool_name} latency_ms={latency_ms}")
                results.append(
                    ToolExecutionResult(
                        tool_name=tool_name,
                        payload=payload,
                        latency_ms=latency_ms,
                        success=True,
                    )
                )
            except Exception as exc:
                latency_ms = int((perf_counter() - start) * 1000)
                logger.warning(f"AI chat tool failed: tool={tool_name} latency_ms={latency_ms} error={exc}")
                results.append(
                    ToolExecutionResult(
                        tool_name=tool_name,
                        payload={},
                        latency_ms=latency_ms,
                        success=False,
                        error=str(exc),
                    )
                )
        return results, decision.denied

    def _run_with_retry(self, *, tool_name: str, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                tool = self._tools[tool_name]
                return tool.run(user_id=user_id, context=context)
            except Exception as exc:  # pragma: no cover - defensive retry
                last_error = exc
        assert last_error is not None
        raise last_error
