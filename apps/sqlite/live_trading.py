"""Live trading management module."""

import json
import sqlite3
from typing import Any, Dict, List, Optional

from apps.logger import logger


class LiveTradingManager:
    """Live trading management operations."""

    db_path: str

    def create_live_session(
        self,
        user_id: int,
        session_name: Optional[str] = None,
        mode: str = "paper",
        max_total_risk_pct: float = 2.0,
        max_positions: int = 5,
        max_correlation: float = 0.7,
        max_drawdown_pct: float = 10.0,
        trading_hours_start: Optional[str] = None,
        trading_hours_end: Optional[str] = None,
        allowed_days: Optional[List[int]] = None,
    ) -> int:
        """Create a new live trading session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            allowed_days_json = json.dumps(allowed_days) if allowed_days else None

            query = """
            INSERT INTO live_trading_sessions (
                user_id, session_name, mode,
                max_total_risk_pct, max_positions, max_correlation, max_drawdown_pct,
                trading_hours_start, trading_hours_end, allowed_days,
                status, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'stopped', NULL)
            """

            cursor.execute(
                query,
                (
                    user_id,
                    session_name,
                    mode,
                    max_total_risk_pct,
                    max_positions,
                    max_correlation,
                    max_drawdown_pct,
                    trading_hours_start,
                    trading_hours_end,
                    allowed_days_json,
                ),
            )
            session_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Live trading session {session_id} created for user {user_id}")
            return int(session_id) if session_id is not None else 0

        except Exception as e:
            logger.error(f"Error creating live session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_live_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a live trading session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM live_trading_sessions WHERE session_id = ?"
            cursor.execute(query, (session_id,))
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)
            if result.get("allowed_days"):
                try:
                    result["allowed_days"] = json.loads(result["allowed_days"])
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to decode allowed_days for session {session_id}"
                    )
                    pass
            return result

        except Exception as e:
            logger.error(f"Error getting live session: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_user_live_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve all live sessions for a user."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT * FROM live_trading_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
            """
            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                res = dict(row)
                if res.get("allowed_days"):
                    try:
                        res["allowed_days"] = json.loads(res["allowed_days"])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to decode allowed_days for session {res.get('session_id')}"
                        )
                        pass
                results.append(res)
            return results

        except Exception as e:
            logger.error(f"Error getting user live sessions: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def update_live_session(self, session_id: int, **kwargs: Any) -> bool:
        """Update a live trading session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            update_fields: List[str] = []
            values: List[Any] = []

            allowed_fields = [
                "session_name",
                "status",
                "mode",
                "max_total_risk_pct",
                "max_positions",
                "max_correlation",
                "max_drawdown_pct",
                "trading_hours_start",
                "trading_hours_end",
                "allowed_days",
                "started_at",
                "stopped_at",
                "last_heartbeat",
                "error_message",
                "total_signals_detected",
                "total_signals_executed",
                "total_signals_rejected",
            ]

            for field in allowed_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = ?")
                    val = kwargs[field]
                    if field == "allowed_days" and isinstance(val, list):
                        val = json.dumps(val)
                    values.append(val)

            if not update_fields:
                return False

            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(session_id)

            query = (
                "UPDATE live_trading_sessions SET "
                + ", ".join(update_fields)
                + " WHERE session_id = ?"
            )
            cursor.execute(query, values)
            conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error updating live session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def delete_live_session(self, session_id: int) -> bool:
        """Delete a live trading session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(
                "DELETE FROM live_trading_sessions WHERE session_id = ?", (session_id,)
            )

            if cursor.rowcount == 0:
                logger.warning(f"Live session {session_id} not found.")
                return False

            conn.commit()
            logger.info(f"Live session {session_id} deleted.")
            return True

        except Exception as e:
            logger.error(f"Error deleting live session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def add_strategy_to_session(
        self,
        session_id: int,
        strategy_version_id: int,
        symbols: List[str],
        timeframes: List[str],
        max_risk_per_trade_pct: float = 1.0,
        position_size_type: str = "risk",
        position_size_value: float = 1.0,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add a strategy to a live session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            symbols_json = json.dumps(symbols)
            timeframes_json = json.dumps(timeframes)
            params_json = json.dumps(strategy_params) if strategy_params else None

            query = """
            INSERT INTO session_strategies (
                session_id, strategy_version_id, symbols, timeframes,
                max_risk_per_trade_pct, position_size_type, position_size_value,
                strategy_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    session_id,
                    strategy_version_id,
                    symbols_json,
                    timeframes_json,
                    max_risk_per_trade_pct,
                    position_size_type,
                    position_size_value,
                    params_json,
                ),
            )
            rel_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Strategy {strategy_version_id} added to session {session_id}")
            return int(rel_id) if rel_id is not None else 0

        except Exception as e:
            logger.error(f"Error adding strategy to session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_session_strategies(self, session_id: int) -> List[Dict[str, Any]]:
        """Retrieve all strategies in a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT ss.*, sv.version, s.name as strategy_name
            FROM session_strategies ss
            JOIN strategy_versions sv ON ss.strategy_version_id = sv.id
            JOIN strategies s ON sv.strategy_id = s.id
            WHERE ss.session_id = ?
            """
            cursor.execute(query, (session_id,))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                res = dict(row)
                try:
                    res["symbols"] = json.loads(res["symbols"])
                    res["timeframes"] = json.loads(res["timeframes"])
                    if res.get("strategy_params"):
                        res["strategy_params"] = json.loads(res["strategy_params"])
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse strategy JSON fields for session {res.get('session_id')}"
                    )
                    pass
                results.append(res)
            return results

        except Exception as e:
            logger.error(f"Error getting session strategies: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def remove_strategy_from_session(
        self, session_id: int, strategy_version_id: int
    ) -> bool:
        """Remove a strategy from a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            DELETE FROM session_strategies
            WHERE session_id = ? AND strategy_version_id = ?
            """
            cursor.execute(query, (session_id, strategy_version_id))
            conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error removing strategy from session: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def create_live_signal(
        self,
        session_id: int,
        strategy_version_id: int,
        symbol: str,
        timeframe: str,
        signal_type: str,
        signal_time: str,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        risk_pips: Optional[float] = None,
        risk_usd: Optional[float] = None,
        position_size: Optional[float] = None,
        reward_risk_ratio: Optional[float] = None,
        signal_reason: Optional[str] = None,
        signal_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a new live signal."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            signal_data_json = json.dumps(signal_data) if signal_data else None

            query = """
            INSERT INTO live_signals (
                session_id, strategy_version_id, symbol, timeframe,
                signal_type, signal_time, entry_price, stop_loss, take_profit,
                risk_pips, risk_usd, position_size, reward_risk_ratio,
                signal_reason, signal_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    session_id,
                    strategy_version_id,
                    symbol,
                    timeframe,
                    signal_type,
                    signal_time,
                    entry_price,
                    stop_loss,
                    take_profit,
                    risk_pips,
                    risk_usd,
                    position_size,
                    reward_risk_ratio,
                    signal_reason,
                    signal_data_json,
                ),
            )
            signal_id = cursor.lastrowid
            conn.commit()

            return int(signal_id) if signal_id is not None else 0

        except Exception as e:
            logger.error(f"Error creating live signal: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_live_signal(self, signal_id: int, status: str, **kwargs: Any) -> bool:
        """Update a live signal status."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            update_fields = ["status = ?", "processed_at = CURRENT_TIMESTAMP"]
            values: List[Any] = [status]

            # Security: Whitelist allowed fields to prevent SQL injection via keys
            allowed_fields = [
                "entry_price",
                "stop_loss",
                "take_profit",
                "risk_pips",
                "risk_usd",
                "position_size",
                "reward_risk_ratio",
                "rejection_reason",
                "position_id",
                "signal_data",
            ]

            for k, v in kwargs.items():
                if k in allowed_fields:
                    update_fields.append(f"{k} = ?")
                    # Handle dict/list values that need JSON serialization
                    if k == "signal_data" and isinstance(v, (dict, list)):
                        values.append(json.dumps(v))
                    else:
                        values.append(v)
                else:
                    logger.warning(f"Ignored unknown or unauthorized update field: {k}")

            values.append(signal_id)

            query = (
                "UPDATE live_signals SET "
                + ", ".join(update_fields)
                + " WHERE signal_id = ?"
            )
            cursor.execute(query, values)
            conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error updating live signal: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_session_signals(
        self, session_id: int, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve signals for a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM live_signals WHERE session_id = ?"
            params: List[Any] = [session_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY signal_time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting session signals: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_live_position(
        self,
        session_id: int,
        signal_id: Optional[int],
        mt5_ticket: int,
        symbol: str,
        type: str,
        open_time: str,
        open_price: float,
        position_size: float,
        **kwargs: Any,
    ) -> int:
        """Create a new live position."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO live_positions (
                session_id, signal_id, mt5_ticket, symbol, type,
                open_time, open_price, position_size,
                current_price, current_profit, current_profit_pct,
                initial_stop_loss, current_stop_loss,
                initial_take_profit, current_take_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    session_id,
                    signal_id,
                    mt5_ticket,
                    symbol,
                    type,
                    open_time,
                    open_price,
                    position_size,
                    open_price,  # current_price starts as open_price
                    kwargs.get("initial_stop_loss"),
                    kwargs.get("initial_stop_loss"),  # current starts as initial
                    kwargs.get("initial_take_profit"),
                    kwargs.get("initial_take_profit"),  # current starts as initial
                ),
            )
            pos_id = cursor.lastrowid
            conn.commit()

            return int(pos_id) if pos_id is not None else 0

        except Exception as e:
            logger.error(f"Error creating live position: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_live_position(self, position_id: int, **kwargs: Any) -> bool:
        """Update a live position."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            update_fields = []
            values = []

            # Security: Whitelist allowed fields to prevent SQL injection via keys
            allowed_fields = [
                "mt5_ticket",
                "mt5_order",
                "current_price",
                "current_profit",
                "current_profit_pct",
                "current_stop_loss",
                "current_take_profit",
                "breakeven_activated",
                "trailing_stop_activated",
                "partial_close_count",
                "status",
                "close_reason",
                "close_time",
                "close_price",
                "final_profit",
                "final_profit_pct",
            ]

            for k, v in kwargs.items():
                if k in allowed_fields:
                    update_fields.append(f"{k} = ?")
                    values.append(v)
                else:
                    logger.warning(
                        f"Ignored unknown or unauthorized update field for position: {k}"
                    )

            if not update_fields:
                return False

            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(position_id)

            query = (
                "UPDATE live_positions SET "
                + ", ".join(update_fields)
                + " WHERE position_id = ?"
            )
            cursor.execute(query, values)
            conn.commit()

            return True

        except Exception as e:
            logger.error(f"Error updating live position: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_live_position(self, position_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single live position."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM live_positions WHERE position_id = ?"
            cursor.execute(query, (position_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error(f"Error getting live position {position_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_session_positions(
        self, session_id: int, status: str = "open"
    ) -> List[Dict[str, Any]]:
        """Retrieve positions for a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM live_positions WHERE session_id = ? AND status = ?"
            cursor.execute(query, (session_id, status))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting session positions: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_position_event(
        self,
        position_id: int,
        event_type: str,
        price: Optional[float] = None,
        size: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        profit: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a position event log."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata) if metadata else None

            query = """
            INSERT INTO live_position_events (
                position_id, event_type, price, size, stop_loss, take_profit,
                profit, reason, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                query,
                (
                    position_id,
                    event_type,
                    price,
                    size,
                    stop_loss,
                    take_profit,
                    profit,
                    reason,
                    metadata_json,
                ),
            )
            event_id = cursor.lastrowid
            if event_id is None:
                raise ValueError("Failed to retrieve event ID after insertion.")

            conn.commit()
            return int(event_id)

        except Exception as e:
            logger.error(f"Error creating position event: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def create_session_log(
        self,
        session_id: int,
        log_level: str,
        log_category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create a log entry for a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            details_json = json.dumps(details) if details else None

            query = """
            INSERT INTO live_session_logs (session_id, log_level, log_category, message, details)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(
                query, (session_id, log_level, log_category, message, details_json)
            )
            log_id = cursor.lastrowid
            if log_id is None:
                raise ValueError("Failed to retrieve log ID after insertion.")

            conn.commit()
            return int(log_id)

        except Exception as e:
            logger.error(f"Error creating session log: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_session_logs(
        self,
        session_id: int,
        log_level: Optional[str] = None,
        log_category: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve logs for a session."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM live_session_logs WHERE session_id = ?"
            params: List[Any] = [session_id]

            if log_level:
                query += " AND log_level = ?"
                params.append(log_level)

            if log_category:
                query += " AND log_category = ?"
                params.append(log_category)

            query += " ORDER BY log_time DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                if result.get("details"):
                    try:
                        result["details"] = json.loads(result["details"])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to decode details for log {result.get('log_id')}"
                        )
                        pass
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error getting session logs: {e}")
            raise
        finally:
            if conn:
                conn.close()
