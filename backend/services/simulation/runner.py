"""High-level simulation run orchestration."""

from __future__ import annotations

from typing import Any, Mapping

from backend.common.logger import logger
from backend.services.simulation.config import SimulationConfig
from backend.services.simulation.data_preparation import (
    PreparedSimulationData,
    SimulationDataPreparer,
)
from backend.services.simulation.results import SimulationRun, SimulationRunResult


class SimulationRunner:
    """Parse config, prepare data, reset runtime, and execute simulation."""

    def __init__(
        self,
        engine: Any,
        data_preparer: SimulationDataPreparer | None = None,
    ) -> None:
        self.engine = engine
        self.data_preparer = data_preparer or SimulationDataPreparer(engine)

    def run(self, config: SimulationConfig | Mapping[str, Any]) -> SimulationRunResult:
        parsed = self._parse_config(config)
        self.engine.reset_runtime(parsed.account)
        prepared = self.data_preparer.prepare(parsed)
        processed_ticks = self._run_prepared(prepared, parsed)
        result = self.engine.get_run_result(processed_ticks=processed_ticks)
        metadata = self._metadata(parsed, prepared, result)
        self._report_if_requested(parsed, metadata)
        
        sim_result = SimulationRunResult.from_run_result(
            parsed,
            prepared,
            result,
            metadata=metadata,
        )
        
        # Automatic DB persistence if configured
        if parsed.reporting.save_to_db and parsed.reporting.user_id is not None:
            self._save_to_database(parsed, sim_result)
            
        return sim_result

    @staticmethod
    def _save_to_database(config: SimulationConfig, result: SimulationRunResult) -> None:
        """Persist simulation run to database."""
        from backend.data.database.sqlite.database_operations import DatabaseManager
        db = DatabaseManager()
        
        try:
            backtest_id = config.reporting.backtest_id
            
            if backtest_id is None:
                # Hash config for uniqueness if creating new
                config_dict = config.to_dict() if hasattr(config, "to_dict") else {}
                config_hash = str(hash(json.dumps(config_dict, sort_keys=True, default=str)))

                backtest_id = db.create_backtest_run(
                    strategy_name=config.strategy.name,
                    strategy_version="1.0.0",
                    start_date=pd.Timestamp(result.start).to_pydatetime(),
                    end_date=pd.Timestamp(result.end).to_pydatetime(),
                    engine_type=config.engine_type,
                    data_resolution=result.metadata.get("data_resolution", "trading_timeframe"),
                    config_hash=config_hash,
                    symbols=list(config.data.symbols),
                    timeframes=[config.data.timeframe],
                    initial_balance=float(config.account.initial_balance),
                    alias=config.reporting.alias,
                    description=config.reporting.description,
                    user_id=config.reporting.user_id,
                )
            
            # Save metrics and status
            db.update_backtest_status(
                backtest_id=backtest_id,
                status="completed",
                final_balance=float(result.final_balance),
            )
            
            if result.trades:
                db.save_backtest_trades(backtest_id, result.trades)
            if result.equity_curve:
                db.save_backtest_equity_curve(backtest_id, result.equity_curve)
                
            logger.info(f"Simulation {backtest_id} persisted to database for user {config.reporting.user_id}")
        except Exception as exc:
            logger.error(f"Failed to persist simulation to database: {exc}")

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
