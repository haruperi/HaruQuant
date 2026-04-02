"""Shared auth/session guards for simulator routes."""

from __future__ import annotations

from typing import Any

from .session_coordinator import SessionCoordinator
from .session_runtime import SimulatorSession


def get_owned_session_record(
    *,
    coordinator: SessionCoordinator[SimulatorSession],
    session_id: int,
    user_id: int,
) -> dict[str, Any]:
    return coordinator.get_owned_metadata(session_id, user_id).as_record()


def get_running_session(
    *,
    coordinator: SessionCoordinator[SimulatorSession],
    session_id: int,
) -> SimulatorSession:
    return coordinator.require_runtime(session_id)
