"""Simulator database manager for storing simulated deals and sessions."""

from __future__ import annotations

import json
import sqlite3
from contextlib import suppress
from datetime import datetime
from typing import Any


class SimulatorManager:
    """SQLite operations for trade simulator data."""

    db_path: str

    @staticmethod
    def _format_time(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return ""
        return str(value)

    def create_simulation_session(self, user_id: int, config: dict[str, Any]) -> int:
        """Create a simulator session record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        config_json = json.dumps(config) if config else None
        start_time = self._format_time(config.get("start_time"))
        end_time = self._format_time(config.get("end_time"))

        cursor.execute(
            """
            INSERT INTO simulation_sessions (
                user_id, session_name, mode, status, symbol, timeframe,
                start_time, end_time, initial_balance, speed_multiplier,
                current_bar_index, total_bars, replay_source, replay_backtest_id,
                replay_file_name, config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                config.get("session_name"),
                config.get("mode", "manual"),
                config.get("status", "running"),
                config.get("symbol"),
                config.get("timeframe"),
                start_time or None,
                end_time or None,
                config.get("initial_balance"),
                config.get("speed_multiplier", 1.0),
                config.get("current_bar_index", 0),
                config.get("total_bars"),
                config.get("replay_source"),
                config.get("replay_backtest_id"),
                config.get("replay_file_name"),
                config_json,
            ),
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return int(session_id) if session_id is not None else 0

    def update_simulation_session(self, session_id: int, **kwargs: Any) -> bool:
        """Update a simulator session record."""
        allowed_fields = {
            "session_name",
            "mode",
            "status",
            "symbol",
            "timeframe",
            "start_time",
            "end_time",
            "initial_balance",
            "speed_multiplier",
            "current_bar_index",
            "total_bars",
            "replay_source",
            "replay_backtest_id",
            "replay_file_name",
            "config",
            "completed_at",
        }

        update_fields = []
        values = []
        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            if key in {"start_time", "end_time", "completed_at"}:
                value = self._format_time(value) or None
            if key == "config" and isinstance(value, (dict, list)):
                value = json.dumps(value)
            update_fields.append(f"{key} = ?")
            values.append(value)

        if not update_fields:
            return False

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(session_id)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE simulation_sessions SET "
            + ", ".join(update_fields)
            + " WHERE session_id = ?",
            values,
        )
        conn.commit()
        conn.close()
        return True

    def update_session_status(self, session_id: int, status: str) -> bool:
        """Update session status."""
        completed_at = datetime.utcnow().isoformat() if status == "completed" else None
        return self.update_simulation_session(
            session_id, status=status, completed_at=completed_at
        )

    def save_trade(self, session_id: int, trade: dict[str, Any]) -> int:
        """Persist a simulator trade for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO simulation_trades (
                session_id, time, symbol, side, price, volume, sl, tp,
                pnl, reason, source, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                self._format_time(trade.get("time")) or None,
                trade.get("symbol"),
                trade.get("side"),
                trade.get("price"),
                trade.get("volume"),
                trade.get("sl"),
                trade.get("tp"),
                trade.get("pnl"),
                trade.get("reason"),
                trade.get("source"),
                json.dumps(trade) if trade else None,
            ),
        )
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return int(trade_id) if trade_id is not None else 0

    def get_simulation_session(self, session_id: int) -> dict[str, Any] | None:
        """Fetch a simulator session by id."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM simulation_sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        if data.get("config"):
            with suppress(json.JSONDecodeError):
                data["config"] = json.loads(data["config"])
        return data

    def list_simulation_sessions(
        self, user_id: int, status: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List simulator sessions for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        params: list[Any] = [user_id]
        query = "SELECT * FROM simulation_sessions WHERE user_id = ?"
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        results = []
        for row in rows:
            data = dict(row)
            if data.get("config"):
                with suppress(json.JSONDecodeError):
                    data["config"] = json.loads(data["config"])
            results.append(data)
        return results

    def get_simulation_trades(self, session_id: int) -> list[dict[str, Any]]:
        """Return stored trades for a session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM simulation_trades WHERE session_id = ? ORDER BY time",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def save_simulation_state(self, session_id: int, current_bar_index: int) -> bool:
        """Persist the current bar index for resume."""
        return self.update_simulation_session(
            session_id, current_bar_index=current_bar_index
        )

    def get_paused_simulation_sessions(self, user_id: int) -> list[dict[str, Any]]:
        """Get paused sessions for resume."""
        return self.list_simulation_sessions(
            user_id=user_id, status="paused", limit=200
        )

    def delete_simulation_session(self, session_id: int) -> bool:
        """Delete a simulator session and its trades."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(
            "DELETE FROM simulation_sessions WHERE session_id = ?",
            (session_id,),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def delete_simulation_sessions_older_than(self, days: int = 7) -> int:
        """Delete sessions older than the given number of days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute(
            "DELETE FROM simulation_sessions WHERE created_at < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return int(count)

    def save_simulator_deal(self, deal: dict[str, Any]) -> None:
        """Persist a simulated deal."""
        formatted_time = self._format_time(deal.get("time"))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO simulator_deals (
                time, magic, symbol, type, direction, volume, price, spread, sl, tp,
                commission, margin_required, fee, swap, profit, comment, reason,
                entry_reason, session_id
            ) VALUES (
                :time, :magic, :symbol, :type, :direction, :volume, :price, :spread, :sl, :tp,
                :commission, :margin_required, :fee, :swap, :profit, :comment, :reason,
                :entry_reason, :session_id
            )
            """,
            {
                "time": formatted_time,
                "magic": deal.get("magic"),
                "symbol": deal.get("symbol"),
                "type": deal.get("type"),
                "direction": deal.get("direction"),
                "volume": deal.get("volume"),
                "price": deal.get("price"),
                "spread": deal.get("spread"),
                "sl": deal.get("sl"),
                "tp": deal.get("tp"),
                "commission": deal.get("commission"),
                "margin_required": deal.get("margin_required"),
                "fee": deal.get("fee"),
                "swap": deal.get("swap"),
                "profit": deal.get("profit"),
                "comment": deal.get("comment"),
                "reason": deal.get("reason"),
                "entry_reason": deal.get("entry_reason"),
                "session_id": deal.get("session_id"),
            },
        )
        conn.commit()
        conn.close()

    def load_simulator_deals(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        """Load simulated deals from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT time, magic, symbol, type, direction, volume, price, spread, sl, tp,
                   commission, margin_required, fee, swap, profit, comment, reason,
                   entry_reason, session_id
            FROM simulator_deals
            WHERE time BETWEEN ? AND ?
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]
