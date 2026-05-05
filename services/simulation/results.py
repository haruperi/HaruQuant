"""Standard simulation result objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from services.simulation.config import SimulationConfig

if TYPE_CHECKING:
    from services.execution.core import RunResult, TradeRecord
    from services.simulation.data_preparation import PreparedSimulationData


@dataclass(frozen=True)
class SimulationRunResult:
    """Standard result returned by ``Engine.run(config)``."""

    config: SimulationConfig
    metadata: Mapping[str, Any]
    prepared: "PreparedSimulationData"
    result: "RunResult"
    metrics: Mapping[str, Any]

    @classmethod
    def from_run_result(
        cls,
        config: SimulationConfig,
        prepared: "PreparedSimulationData",
        run_result: "RunResult",
        metadata: Mapping[str, Any] | None = None,
    ) -> "SimulationRunResult":
        from dataclasses import asdict
        # Extract values from metadata if provided by SimulationRunner
        meta_dict = dict(metadata or {})
        processed_ticks = int(meta_dict.get("processed_ticks", getattr(run_result, "processed_ticks", 0)))
        final_balance = float(
            meta_dict.get(
                "final_balance",
                getattr(run_result, "final_balance", config.account.initial_balance),
            )
        )
        final_equity = float(
            meta_dict.get(
                "final_equity",
                getattr(run_result, "final_equity", final_balance),
            )
        )
        
        symbol_summary = build_symbol_summary(config.data.symbols, run_result.trades)
        
        # Merge metrics (Output/Results)
        metrics = {
            "processed_ticks": processed_ticks,
            "trade_count": len(run_result.trades),
            "equity_points": len(run_result.equity_curve),
            "initial_balance": float(config.account.initial_balance),
            "final_balance": final_balance,
            "final_equity": final_equity,
            "total_profit": float(final_balance - config.account.initial_balance),
            "total_return": (
                float((final_balance - config.account.initial_balance) / config.account.initial_balance)
                if config.account.initial_balance > 0.0
                else 0.0
            ),
            "symbol_summary": symbol_summary,
        }
        
        # Merge metadata (Inputs/Environment)
        # We flatten the config attributes directly into metadata
        merged_metadata = dict(asdict(config))
        # Add preparation metadata and other extras
        if "prepared" in meta_dict:
            merged_metadata["prepared"] = meta_dict["prepared"]
        merged_metadata["warnings"] = meta_dict.get("warnings", ())
        merged_metadata.update(metrics)
        
        return cls(
            config=config,
            metadata=merged_metadata,
            prepared=prepared,
            result=run_result,
            metrics=metrics,
        )

    @property
    def processed_ticks(self) -> int:
        return int(self.metrics.get("processed_ticks", 0))

    @property
    def final_balance(self) -> float:
        return float(self.metrics.get("final_balance", 0.0))

    @property
    def final_equity(self) -> float:
        return float(self.metrics.get("final_equity", self.final_balance))

    @property
    def total_profit(self) -> float:
        return float(self.metrics.get("total_profit", 0.0))

    @property
    def total_return(self) -> float:
        return float(self.metrics.get("total_return", 0.0))

    @property
    def trade_count(self) -> int:
        return int(self.metrics.get("trade_count", 0))

    @property
    def symbol_summary(self) -> Mapping[str, Mapping[str, float]]:
        return self.metrics.get("symbol_summary", {})

    @property
    def warnings(self) -> tuple[Any, ...]:
        return tuple(self.metadata.get("warnings", ()))

    @property
    def trades(self) -> list["TradeRecord"]:
        return self.result.trades


def build_symbol_summary(
    symbols: tuple[str, ...],
    trades: list["TradeRecord"],
) -> Mapping[str, Mapping[str, float]]:
    """Build a PnL summary for each symbol in the backtest."""
    summary = {s: {"trades": 0.0, "pnl": 0.0} for s in symbols}
    for trade in trades:
        symbol = str(getattr(trade, "symbol", "") or "")
        if symbol not in summary:
            summary[symbol] = {"trades": 0.0, "pnl": 0.0}
        summary[symbol]["trades"] += 1.0
        summary[symbol]["pnl"] += float(getattr(trade, "profit_loss", 0.0) or 0.0)
    return summary


# Backward-compatible name for Phase 5 tests/imports during migration.
SimulationRun = SimulationRunResult
