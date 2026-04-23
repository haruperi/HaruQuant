"""High-level simulation run orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.common.logger import logger
from backend.services.execution.core import RunResult
from backend.services.simulation.config import SimulationConfig
from backend.services.simulation.data_preparation import (
    PreparedSimulationData,
    SimulationDataPreparer,
)


@dataclass(frozen=True)
class SimulationRun:
    """Completed simulation payload with config and preparation metadata."""

    config: SimulationConfig
    prepared: PreparedSimulationData
    result: RunResult
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def trades(self):
        return self.result.trades

    @property
    def equity_curve(self):
        return self.result.equity_curve

    @property
    def processed_ticks(self) -> int:
        return int(self.result.processed_ticks)

    @property
    def final_balance(self) -> float:
        return float(self.result.final_balance)

    @property
    def final_equity(self) -> float:
        return float(self.result.final_equity)


class SimulationRunner:
    """Parse config, prepare data, reset runtime, and execute simulation."""

    def __init__(
        self,
        engine: Any,
        data_preparer: SimulationDataPreparer | None = None,
    ) -> None:
        self.engine = engine
        self.data_preparer = data_preparer or SimulationDataPreparer(engine)

    def run(self, config: SimulationConfig | Mapping[str, Any]) -> SimulationRun:
        parsed = self._parse_config(config)
        self.engine.reset_runtime(parsed.account)
        prepared = self.data_preparer.prepare(parsed)
        processed_ticks = self._run_prepared(prepared, parsed)
        result = self.engine.get_run_result(processed_ticks=processed_ticks)
        metadata = self._metadata(parsed, prepared, result)
        self._report_if_requested(parsed, metadata)
        return SimulationRun(
            config=parsed,
            prepared=prepared,
            result=result,
            metadata=metadata,
        )

    @staticmethod
    def _parse_config(config: SimulationConfig | Mapping[str, Any]) -> SimulationConfig:
        if isinstance(config, SimulationConfig):
            return config
        return SimulationConfig.from_dict(config)

    def _run_prepared(
        self,
        prepared: PreparedSimulationData,
        config: SimulationConfig,
    ) -> int:
        processed_ticks = self.engine.run_prepared(prepared, config)
        return int(processed_ticks or 0)

    @staticmethod
    def _metadata(
        config: SimulationConfig,
        prepared: PreparedSimulationData,
        result: RunResult,
    ) -> dict[str, Any]:
        return {
            "engine_type": config.engine_type,
            "symbols": tuple(config.data.symbols),
            "timeframe": config.data.timeframe,
            "data_source": config.data.source,
            "tick_model": config.execution.tick_model,
            "spread_model": config.execution.spread_model,
            "processed_ticks": int(result.processed_ticks),
            "trade_count": len(result.trades),
            "equity_points": len(result.equity_curve),
            "final_balance": float(result.final_balance),
            "final_equity": float(result.final_equity),
            "prepared": dict(prepared.metadata),
        }

    @staticmethod
    def _report_if_requested(
        config: SimulationConfig,
        metadata: Mapping[str, Any],
    ) -> None:
        if not config.reporting.print_summary:
            return
        logger.info(
            "Simulation completed: "
            f"engine={metadata['engine_type']} "
            f"symbols={metadata['symbols']} "
            f"ticks={metadata['processed_ticks']} "
            f"trades={metadata['trade_count']} "
            f"final_equity={metadata['final_equity']:.2f}"
        )
