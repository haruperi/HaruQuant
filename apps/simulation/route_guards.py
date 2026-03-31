"""Shared auth/session guards for simulator routes."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from .session_manager import SimulatorSessionManager
from .session_runtime import SimulatorSession


def get_owned_session_record(
    *,
    db_manager: Any,
    session_id: int,
    user_id: int,
) -> dict[str, Any]:
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def get_running_session(
    *,
    active_sessions: SimulatorSessionManager[SimulatorSession],
    session_id: int,
) -> SimulatorSession:
    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")
    return active
