"""Live Trading Session Manager.

Wraps the MultiStrategyEngine to be controlled via the API and Database.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from backend.services.live_trading.engine import MultiStrategyEngine
from backend.mcp.mt5_mcp.client import MT5Client
from backend.data.database.sqlite.database_operations import DatabaseManager

logger = logging.getLogger(__name__)


class ExecutionEngineWrapper:
    """Wrapper to expose close_position to the API."""

    def __init__(self, engine: MultiStrategyEngine):
        """Initialize wrapper with engine instance."""
        self.engine = engine

    async def close_position(self, position: Any, reason: str = "manual") -> bool:
        """Close a specific position."""
        engine = self.engine
        if not engine:
            logger.error("Trade object not initialized in engine")
            return False

        trade = engine.trade
        if not trade:
            logger.error("Trade object not initialized in engine")
            return False

        # In a real async/threaded environment, we might need to offload this to the engine loop
        # But MT5 calls are synchronous blocking calls mostly.
        # Ideally, we should use run_in_executor if called from async context.
        try:
            loop = asyncio.get_running_loop()
            ticket = getattr(position, "mt5_ticket", None) or getattr(
                position, "ticket", None
            )
            if not ticket:
                logger.error(f"No ticket found in position: {position}")
                return False

            symbol = getattr(position, "symbol", None)
            if symbol:
                try:
                    filling_mode = engine._get_supported_filling_mode(symbol)
                    trade.SetTypeFilling(int(filling_mode))
                except Exception as exc:
                    logger.warning(f"Failed to set filling mode for {symbol}: {exc}")

            success = await loop.run_in_executor(
                None, lambda: trade.PositionClose(ticket=ticket)
            )
            return bool(success)
        except Exception as e:
            logger.error(f"Error closing position {position}: {e}")
            return False


class LiveTradingSession:
    """Live Trading Session that wraps MultiStrategyEngine."""

    def __init__(self, session_id: int, mt5_client: MT5Client, db: DatabaseManager):
        """Initialize session.

        Args:
            session_id: The ID of the session in the database.
            mt5_client: Initialized MT5 Client.
            db: Database manager instance.
        """
        self.session_id = session_id
        self.mt5_client = mt5_client
        self.db = db
        self.engine: Optional[MultiStrategyEngine] = None
        self._task: Optional[asyncio.Task] = None
        self._execution_engine_wrapper: Optional[ExecutionEngineWrapper] = None

    @property
    def execution_engine(self):
        """Expose execution engine for API calls."""
        if not self._execution_engine_wrapper and self.engine:
            self._execution_engine_wrapper = ExecutionEngineWrapper(self.engine)
        return self._execution_engine_wrapper

    async def start(self):
        """Start the live trading session."""
        logger.info(f"Starting session {self.session_id}")

        # 1. Fetch session configuration from DB
        session_data = self.db.get_live_session(self.session_id)
        if not session_data:
            raise ValueError(f"Session {self.session_id} not found in DB")

        # 2. Build Engine Configuration
        config = self._build_engine_config(session_data)

        # 3. Initialize Engine
        self.engine = MultiStrategyEngine(config=config, client=self.mt5_client)

        # Run initialization in executor to avoid blocking async loop
        loop = asyncio.get_running_loop()
        initialized = await loop.run_in_executor(None, self.engine.initialize)

        if not initialized:
            raise RuntimeError("Failed to initialize MultiStrategyEngine")

        # 4. Start Engine Loop in background task
        # engine.run() is a blocking while loop, so we must wrap it.
        self._task = asyncio.create_task(self._run_engine_loop())

        # Update status
        self.db.update_live_session(self.session_id, status="running")
        logger.info(f"Session {self.session_id} started")

    async def _run_engine_loop(self):
        """Run the blocking engine loop in a separate thread."""
        try:
            loop = asyncio.get_running_loop()
            if self.engine:
                await loop.run_in_executor(None, self.engine.run)
        except Exception as e:
            logger.error(f"Engine loop failed for session {self.session_id}: {e}")
            self.db.update_live_session(self.session_id, status="error")

    async def stop(self):
        """Stop the session."""
        logger.info(f"Stopping session {self.session_id}")

        if self.engine:
            # This is thread-safe enough for a boolean flag flip usually
            self.engine.stop()

        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error awaiting engine task: {e}")

        self.db.update_live_session(self.session_id, status="stopped")

    async def pause(self):
        """Pause the session (disable trading, keep monitoring)."""
        # MultiStrategyEngine uses a file-based state manager usually.
        # But if we want to control it directly, we might need access to its state_manager.
        # self.engine.state_manager.set_paused(True)
        # Assuming state_manager has public methods or we write to the state file.

        # The engine uses `self.config["state"]["file"]`.
        # We can update that file or use the object if accessible.
        if self.engine and self.engine.state_manager:
            loop = asyncio.get_running_loop()
            # Assuming set_paused writes to file, which is I/O
            await loop.run_in_executor(None, lambda: self._set_engine_paused(True))

        self.db.update_live_session(self.session_id, status="paused")

    async def resume(self):
        """Resume the session."""
        if self.engine and self.engine.state_manager:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self._set_engine_paused(False))

        self.db.update_live_session(self.session_id, status="running")

    def _set_engine_paused(self, paused: bool):
        """Set pause state on engine's state manager."""
        if not self.engine or not self.engine.state_manager:
            logger.error("State manager not initialized in engine")
            return

        sm = self.engine.state_manager
        if paused:
            sm.pause()
        else:
            sm.resume()

    def _build_engine_config(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DB session data to Engine Config format."""
        # Fetch strategies for this session from DB
        # The API code passes session_id, but the session_data from `get_live_session`
        # might not include the full strategies list joined.
        # We need to query strategies separately if they aren't in session_data.
        # Apps/api/routes/live.py uses db_manager.get_user_live_sessions / get_live_session
        # Let's assume we need to fetch strategies.

        strategies = self.db.get_session_strategies(self.session_id)
        user = self.db.get_user(user_id=session_data["user_id"])
        username = (user.get("username") if user else "") or ""
        strategy_configs = self._build_strategy_configs(strategies, username)

        # Construct full config
        config = {
            "mt5": {
                "login": 0,  # Placeholder, client is injected
                "password": "",
                "server": "",
            },
            "portfolio": {
                "max_total_positions": session_data.get("max_positions", 20),
                "max_positions_per_symbol": 3,  # Default or from session extra params
                "max_portfolio_risk_percent": session_data.get(
                    "max_total_risk_pct", 10.0
                ),
                "max_correlated_positions": max(
                    1, int(session_data.get("max_correlation", 5))
                ),
            },
            "strategies": strategy_configs,
            "trading": {  # Default fallback trading params
                "timeframe": "M1",
                "volume": 0.01,
                "magic_number": 0,
                "initial_bars": 500,
                "deviation": 10,
            },
            "safety": {
                "min_balance": 100.0,
                "min_margin_level": 100.0,
                "max_positions": session_data.get("max_positions", 20),
                "max_daily_trades": 100,
            },
            "notifications": {"enable_email": False},
            "logging": {
                "dir": "backend/logs/live_session_" + str(self.session_id),
                "level": "INFO",
            },
            "state": {"file": f"backend/data/states/session_{self.session_id}_state.json"},
            "user_id": session_data["user_id"],
        }

        return config

    def _normalize_list(self, value: Any) -> list:
        if isinstance(value, str):
            return [value]
        return value or []

    def _build_strategy_configs(self, strategies: list, username: str) -> list:
        strategy_configs = []
        for strat in strategies:
            try:
                symbols = self._normalize_list(strat.get("symbols"))
                timeframes = self._normalize_list(strat.get("timeframes"))

                if not symbols and strat.get("symbol"):
                    symbols = [strat.get("symbol")]
                if not timeframes and strat.get("timeframe"):
                    timeframes = [strat["timeframe"]]

                strategy_type = (
                    strat.get("strategy_type") or strat.get("category") or "Unknown"
                )

                if not symbols:
                    logger.warning(
                        f"Strategy {strat.get('strategy_version_id')} has no symbols defined"
                    )
                    continue

                for symbol in symbols:
                    for timeframe in timeframes:
                        logger.debug(
                            f"Adding strategy config: {symbol} {strategy_type} {timeframe}"
                        )
                        strategy_configs.append(
                            {
                                "name": f"{symbol}_{strategy_type}_{timeframe}",
                                "strategy_name": strat.get("strategy_name"),
                                "strategy_type": strategy_type,
                                "strategy_id": strat.get("strategy_id"),
                                "strategy_version_id": strat.get("strategy_version_id"),
                                "strategy_version": strat.get("version"),
                                "username": username,
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "magic_number": int(strat.get("magic_number") or 0),
                                "volume": float(
                                    strat.get("position_size_value") or 0.01
                                ),
                                "params": strat.get("strategy_params") or {},
                                "initial_bars": 500,
                            }
                        )
            except Exception as exc:
                logger.error(
                    "Error processing strategy config: %s. Strat keys: %s",
                    exc,
                    list(strat.keys()),
                )
                raise

        return strategy_configs

    def get_status(self) -> Dict[str, Any]:
        """Get lightweight real-time status."""
        if not self.engine:
            return {}

        engine_status = self.engine.get_status()
        portfolio = engine_status.get("portfolio", {})
        strategies = engine_status.get("strategies", [])

        # Aggregate counts
        detected = sum(s.get("signals_detected", 0) for s in strategies)
        executed = sum(s.get("signals_executed", 0) for s in strategies)
        # Trades executed is roughly signals executed for now.
        # StrategyInstance has trades_executed count.
        trades_executed = sum(s.get("trades_executed", 0) for s in strategies)

        # Rejected is detected - executed? Or StrategyInstance tracks it?
        # StrategyInstance tracks trades_failed.
        # engine_status['strategies'] items have: signals_detected, signals_executed
        rejected = detected - executed
        if rejected < 0:
            rejected = 0

        # Strategies dict from engine:
        # {
        #     "name": self.name,
        #     "symbol": self.symbol,
        #     "active_positions": len(self.position_manager.positions),
        #     "signals_detected": self.signal_processor.signals_detected,
        #     "signals_executed": self.trades_executed, # In engine.py _process_strategy logs execution
        #     ...
        # }

        return {
            "session_id": self.session_id,
            "session_name": f"Session {self.session_id}",  # Matches API default
            "status": "running" if self.engine._running else "paused",
            "running": self.engine._running,
            "paused": not self.engine._running,
            "signals_detected": detected,
            "signals_approved": executed,
            "signals_rejected": rejected,
            "positions_opened": trades_executed,
            "positions_closed": 0,  # TODO: Track closed positions in engine
            "active_positions": portfolio.get("total_positions", 0),
            "current_equity": float(portfolio.get("equity", 0.0)),
            "current_balance": float(portfolio.get("balance", 0.0)),
            "account_name": (
                self.mt5_client.account_name
                if hasattr(self.mt5_client, "account_name")
                else None
            ),
            "account_server": self.mt5_client.account_server,
            "account_login": self.mt5_client.account_login,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        # For now, return extended status.
        # This matches SessionStatisticsResponse structure requirement (fields from get_status + more?)
        # SessionStatisticsResponse usually extends SessionStatusResponse
        return self.get_status()
