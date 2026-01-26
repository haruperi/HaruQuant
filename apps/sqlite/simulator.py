"""Simulator database manager for storing simulated deals."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any


class SimulatorManager:
    """SQLite operations for trade simulator data."""

    db_path: str

    def save_simulator_deal(self, deal: dict[str, Any]) -> None:
        """Persist a simulated deal."""
        time_value = deal.get("time")
        if isinstance(time_value, datetime):
            formatted_time = time_value.isoformat()
        elif time_value is None:
            formatted_time = ""
        else:
            formatted_time = str(time_value)

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
