"""Standard simulation result objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.services.execution.core import EquityPoint, RunResult, TradeRecord
from backend.services.simulation.config import SimulationConfig
from backend.services.simulation.data_preparation import PreparedSimulationData


@dataclass(frozen=True)
class SimulationRunResult:
    """Standard result returned by ``Engine.run(config)``."""

    config: SimulationConfig
    prepared: PreparedSimulationData
    run_result: RunResult
    metrics: Mapping[str, Any] = field(default_factory=dict)
    symbol_summary: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def engine_type(self) -> str:
        return self.config.engine_type

    @property
    def symbols(self) -> tuple[str, ...]:
        return self.config.data.symbols

    @property
    def timeframe(self) -> str:
        return self.config.data.timeframe

    @property
    def start(self):
        return self.config.data.start

    @property
    def end(self):
        return self.config.data.end

    @property
    def initial_balance(self) -> float:
        return float(self.config.account.initial_balance)

    @property
    def processed_ticks(self) -> int:
        return int(self.run_result.processed_ticks)

    @property
    def final_balance(self) -> float:
        return float(self.run_result.final_balance)

    @property
    def final_equity(self) -> float:
        return float(self.run_result.final_equity)

    @property
    def total_profit(self) -> float:
        return float(self.final_balance - self.initial_balance)

    @property
    def total_return(self) -> float:
        if self.initial_balance <= 0.0:
            return 0.0
        return float(self.total_profit / self.initial_balance)

    @property
    def trades(self) -> list[TradeRecord]:
        return self.run_result.trades

    @property
    def equity_curve(self) -> list[EquityPoint]:
        return self.run_result.equity_curve

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @classmethod
    def from_run_result(
        cls,
        config: SimulationConfig,
        prepared: PreparedSimulationData,
        run_result: RunResult,
        metadata: Mapping[str, Any] | None = None,
    ) -> "SimulationRunResult":
        symbol_summary = build_symbol_summary(config.data.symbols, run_result.trades)
        metrics = {
            "processed_ticks": int(run_result.processed_ticks),
            "trade_count": len(run_result.trades),
            "equity_points": len(run_result.equity_curve),
            "initial_balance": float(config.account.initial_balance),
            "final_balance": float(run_result.final_balance),
            "final_equity": float(run_result.final_equity),
            "total_profit": float(run_result.final_balance - config.account.initial_balance),
            "total_return": (
                float((run_result.final_balance - config.account.initial_balance) / config.account.initial_balance)
                if config.account.initial_balance > 0.0
                else 0.0
            ),
        }
        return cls(
            config=config,
            prepared=prepared,
            run_result=run_result,
            metrics=metrics,
            symbol_summary=symbol_summary,
            metadata=dict(metadata or {}),
        )


def build_symbol_summary(
    symbols: tuple[str, ...],
    trades: list[TradeRecord],
) -> dict[str, dict[str, float]]:
    summary = {symbol: {"trades": 0.0, "pnl": 0.0} for symbol in symbols}
    for trade in trades:
        symbol = str(getattr(trade, "symbol", "") or "")
        if symbol not in summary:
            summary[symbol] = {"trades": 0.0, "pnl": 0.0}
        summary[symbol]["trades"] += 1.0
        summary[symbol]["pnl"] += float(getattr(trade, "profit_loss", 0.0) or 0.0)
    return summary


# Backward-compatible name for Phase 5 tests/imports during migration.
SimulationRun = SimulationRunResult
