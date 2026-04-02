"""Thin read-only adapters over live session status and runtime health."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from apps.api.routes import live as live_routes
from apps.live.session import LiveTradingSession
from apps.sqlite.live_trading import LiveTradingManager


class _BoundLiveTradingManager(LiveTradingManager):
    """Provide a concrete constructor for live session persistence access."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        self.db_path = db_path or str(project_root / "data" / "database" / "haruquant.db")


class LiveTools:
    """Expose minimal session-state reads for execution oversight workflows."""

    def __init__(
        self,
        *,
        manager: Optional[LiveTradingManager] = None,
        active_sessions: Optional[Dict[int, LiveTradingSession]] = None,
    ) -> None:
        self.manager = manager or _BoundLiveTradingManager()
        self.active_sessions = active_sessions if active_sessions is not None else live_routes.active_sessions

    def live_get_session_status(self, *, session_id: int) -> Dict[str, Any]:
        """Return persisted and runtime-aware live session status."""
        persisted = self.manager.get_live_session(int(session_id))
        if persisted is None:
            raise ValueError(f"Live session {session_id} not found.")
        runtime = self.active_sessions.get(int(session_id))
        if runtime is not None:
            status = runtime.get_status()
            status["persisted_status"] = persisted.get("status")
            status["error_message"] = persisted.get("error_message")
            return status
        return {
            "session_id": persisted.get("session_id"),
            "session_name": persisted.get("session_name"),
            "status": persisted.get("status"),
            "running": False,
            "paused": persisted.get("status") == "paused",
            "signals_detected": persisted.get("total_signals_detected", 0),
            "signals_approved": persisted.get("total_signals_executed", 0),
            "signals_rejected": persisted.get("total_signals_rejected", 0),
            "active_positions": 0,
            "current_equity": 0.0,
            "current_balance": 0.0,
            "error_message": persisted.get("error_message"),
        }

    def live_get_execution_quality(self, *, session_id: int) -> Dict[str, Any]:
        """Return a compact execution-quality summary from session counters."""
        status = self.live_get_session_status(session_id=int(session_id))
        detected = int(status.get("signals_detected", 0) or 0)
        approved = int(status.get("signals_approved", 0) or 0)
        rejected = int(status.get("signals_rejected", 0) or 0)
        approval_rate = (approved / detected) if detected > 0 else 0.0
        rejection_rate = (rejected / detected) if detected > 0 else 0.0
        return {
            "session_id": status.get("session_id"),
            "status": status.get("status"),
            "signals_detected": detected,
            "signals_approved": approved,
            "signals_rejected": rejected,
            "approval_rate": approval_rate,
            "rejection_rate": rejection_rate,
            "active_positions": int(status.get("active_positions", 0) or 0),
            "error_message": status.get("error_message"),
        }
