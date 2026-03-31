"""Session lifecycle helpers for simulator routes."""

from __future__ import annotations

from contextlib import suppress
from typing import Any, Optional

from fastapi import HTTPException, status

from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.utils.logger import logger

from .route_support import refresh_session_risk_state
from .session_manager import SimulatorSessionManager
from .session_runtime import SimulatorSession


def load_strategy_class(
    db_manager: DatabaseManager,
    user_id: int,
    strategy_id: int,
    version_id: int,
):
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    if version is None:
        raise ValueError(f"Strategy version {version_id} not found")
    if strategy is None:
        raise ValueError(f"Strategy {strategy_id} not found")

    user = db_manager.get_user(user_id=user_id)
    username = (user.get("username") if user else "") or ""
    strategy_name = (strategy.get("name") if strategy else "") or ""

    return storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )


def resolve_strategy_version_id(db_manager: DatabaseManager, strategy_id: int) -> int:
    strategy = db_manager.get_strategy(strategy_id)
    if not strategy or not strategy.get("active_version_id"):
        raise ValueError("Strategy or active version not found")
    return int(strategy["active_version_id"])


def resume_or_restore_session(
    *,
    db_manager: DatabaseManager,
    active_sessions: SimulatorSessionManager[SimulatorSession],
    session_id: int,
    session_data: dict[str, Any],
    user_id: int,
) -> dict[str, Any]:
    active = active_sessions.get(session_id)
    if active:
        active.resume()
        return {"session_id": session_id, "status": "running"}

    config = dict(session_data.get("config") or {})
    config["user_id"] = user_id
    config["current_bar_index"] = session_data.get("current_bar_index", 0)
    config["status"] = "running"

    session = SimulatorSession(session_id=session_id, config=config, db=db_manager)
    session.load_historical_bars()
    session.apply_mt5_account_defaults()
    session.refresh_risk_state()
    session.ensure_risk_run()
    active_sessions.put(session_id, session)
    db_manager.update_simulation_session(session_id, status="running")

    return {"session_id": session_id, "status": "running"}


def delete_session_runtime(
    *,
    db_manager: DatabaseManager,
    active_sessions: SimulatorSessionManager[SimulatorSession],
    session_id: int,
) -> dict[str, Any]:
    active = active_sessions.remove(session_id)
    if active:
        active.stop()

    db_manager.delete_simulation_session(session_id)
    return {"session_id": session_id, "status": "deleted"}


def stop_and_save_session_runtime(
    *,
    db_manager: DatabaseManager,
    active_sessions: SimulatorSessionManager[SimulatorSession],
    session_id: int,
    user_id: int,
) -> dict[str, Any]:
    active = active_sessions.remove(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    save_succeeded = False
    risk_snapshot_id: Optional[int] = None
    try:
        backtest_id = active.finalize_for_saved_backtest(user_id)
        refresh_session_risk_state(active)
        risk_snapshot_id = active.persist_current_risk_bundle(backtest_id=backtest_id)
        save_succeeded = True
    except Exception as exc:
        active_sessions.put(session_id, active)
        logger.error(f"Stop and save session failed | session={session_id} err={exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save simulation",
        )
    finally:
        if save_succeeded:
            with suppress(Exception):
                active.stop()

    db_manager.delete_simulation_session(session_id)
    return {
        "session_id": session_id,
        "status": "saved",
        "backtest_id": backtest_id,
        "risk_run_id": active.risk_run_id,
        "risk_snapshot_id": risk_snapshot_id,
    }
