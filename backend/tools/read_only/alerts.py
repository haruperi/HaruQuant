"""Read-only alert and incident chat tools."""

from __future__ import annotations

from typing import Any

from backend.data.database.sqlite.database_operations import DatabaseManager


class AlertHistoryTool:
    name = "alert_history"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def run(self, *, user_id: int, context: dict[str, Any]) -> dict[str, Any]:
        sessions = self.db.get_user_live_sessions(user_id) or []
        logs: list[dict[str, Any]] = []
        for session in sessions[:5]:
            session_logs = self.db.get_session_logs(int(session["session_id"]), limit=20) or []
            logs.extend(
                log for log in session_logs
                if str(log.get("log_level", "")).lower() in {"warning", "error", "critical"}
            )
        logs.sort(key=lambda item: str(item.get("log_time") or ""), reverse=True)
        return {
            "alert_count": len(logs),
            "recent_alerts": [
                {
                    "level": log.get("log_level"),
                    "category": log.get("log_category"),
                    "message": log.get("message"),
                    "log_time": log.get("log_time"),
                }
                for log in logs[:8]
            ],
        }
