"""Thin simulator session wrappers for agent-safe advisory workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.api.routes import simulator as simulator_routes
from apps.simulation.api_models import WhatIfActionRequest
from apps.simulation.session_service import (
    resume_or_restore_session,
    stop_and_save_session_runtime,
)
from apps.simulation.trade_service import (
    evaluate_what_if as evaluate_what_if_runtime,
    preview_trade as preview_trade_runtime,
)


class SimulatorTools:
    """Expose bounded simulator session reads and advisory actions."""

    def __init__(
        self,
        *,
        db_manager: Any = None,
        coordinator: Any = None,
    ) -> None:
        self.db_manager = db_manager or simulator_routes.db_manager
        self.coordinator = coordinator or simulator_routes.session_coordinator

    def sim_list_sessions(self, *, user_id: int, status: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
        """List simulator sessions for one user."""
        return self.db_manager.list_simulation_sessions(user_id=int(user_id), status=status, limit=int(limit))

    def sim_get_session(self, *, session_id: int) -> Dict[str, Any]:
        """Load one persisted simulator session record."""
        session = self.db_manager.get_simulation_session(int(session_id))
        if session is None:
            raise ValueError(f"Simulation session {session_id} not found.")
        return session

    def sim_preview_trade(self, *, session_id: int, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Build a manual-trade governance preview for one running session."""
        active = self.coordinator.require_runtime(int(session_id))
        return preview_trade_runtime(active, dict(trade_request))

    def sim_run_what_if(
        self,
        *,
        session_id: int,
        actions: List[Dict[str, Any]],
        leverage_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a non-mutating what-if analysis on one running session."""
        active = self.coordinator.require_runtime(int(session_id))
        action_models = [
            WhatIfActionRequest(**dict(item))
            for item in actions
        ]
        return evaluate_what_if_runtime(
            active,
            action_models,
            leverage_override,
            refresh_session_risk_state=simulator_routes.refresh_session_risk_state,
        )

    def sim_resume_session(self, *, session_id: int, user_id: int) -> Dict[str, Any]:
        """Resume one paused simulator session."""
        session = self.sim_get_session(session_id=int(session_id))
        if int(session.get("user_id") or 0) != int(user_id):
            raise ValueError("You do not have permission to resume this simulation session.")
        return resume_or_restore_session(
            db_manager=self.db_manager,
            coordinator=self.coordinator,
            session_id=int(session_id),
            session_data=session,
            user_id=int(user_id),
        )

    def sim_stop_and_save(self, *, session_id: int, user_id: int) -> Dict[str, Any]:
        """Persist one running simulator session as saved artifacts."""
        session = self.sim_get_session(session_id=int(session_id))
        if int(session.get("user_id") or 0) != int(user_id):
            raise ValueError("You do not have permission to stop and save this simulation session.")
        return stop_and_save_session_runtime(
            db_manager=self.db_manager,
            coordinator=self.coordinator,
            session_id=int(session_id),
            user_id=int(user_id),
        )
