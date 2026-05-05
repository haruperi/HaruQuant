"""Trading simulator API routes."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)

from backend_retiring.api.auth_utils import get_user_id_from_token
from haruquant.simulation import AdvanceRequest, ManualTradeRequest, OrderModifyRequest, PendingOrderRequest, PositionModifyRequest, SeekRequest, SeekTradeRequest, SimulationStartRequest, SimulationUpdateRequest, WhatIfRequest
from haruquant.utils import logger
from haruquant.simulation import SessionCoordinator, SimulatorSessionManager
from haruquant.simulation import get_owned_session_record, get_running_session
from haruquant.simulation import SQLiteSessionRuntimeStore
from haruquant.simulation import build_session_state_response, collect_positions_orders, refresh_session_risk_state
from haruquant.simulation import delete_session_runtime, load_strategy_class, resolve_strategy_version_id, resume_or_restore_session, stop_and_save_session_runtime
from haruquant.simulation import SimulatorSession
from haruquant.simulation import close_position as close_position_runtime, delete_order as delete_order_runtime, evaluate_what_if as evaluate_what_if_runtime, execute_trade as execute_trade_runtime, modify_order as modify_order_runtime, modify_position as modify_position_runtime, partial_close_position as partial_close_position_runtime, place_pending_order as place_pending_order_runtime, preview_trade as preview_trade_runtime
from data.database.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)


active_sessions = SimulatorSessionManager[SimulatorSession]()
session_coordinator = SessionCoordinator(
    store=SQLiteSessionRuntimeStore(db_manager),
    runtimes=active_sessions,
)


def cleanup_stale_simulation_leases() -> int:
    """Clear expired simulator runtime leases during application startup."""
    cleared = session_coordinator.clear_expired_leases()
    if cleared > 0:
        logger.info(f"Cleared {cleared} stale simulator session lease(s)")
    return cleared


def _get_authenticated_user_id(authorization: str = AUTH_HEADER) -> int:
    return get_user_id_from_token(authorization)


def _get_owned_session(
    session_id: int,
    user_id: Annotated[int, Depends(_get_authenticated_user_id)],
) -> Dict[str, Any]:
    return get_owned_session_record(
        coordinator=session_coordinator,
        session_id=session_id,
        user_id=user_id,
    )


def _get_running_session(
    session_id: int,
    _session: Annotated[Dict[str, Any], Depends(_get_owned_session)],
) -> SimulatorSession:
    return get_running_session(coordinator=session_coordinator, session_id=session_id)


@router.post("/start")
async def start_simulation(
    payload: SimulationStartRequest,
    user_id: Annotated[int, Depends(_get_authenticated_user_id)],
):
    """Start a new simulation session."""
    try:
        config = payload.model_dump()
        config["user_id"] = user_id

        if payload.mode == "replay":
            if payload.replay_source == "csv" and not payload.replay_backtest_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Import CSV via /api/import/sqx and provide replay_backtest_id",
                )
            if payload.replay_backtest_id:
                # Load backtest record for metadata
                backtest_run = db_manager.get_backtest_run(payload.replay_backtest_id)
                if backtest_run:
                    # For replay mode, we ALWAYS adopt metadata from the backtest source
                    # to ensure consistency with the recorded trades.
                    config["symbol"] = backtest_run.get("symbol") or config.get("symbol")
                    config["timeframe"] = backtest_run.get("timeframe") or config.get("timeframe")
                    config["start_time"] = backtest_run.get("start_date") or config.get("start_time")
                    config["end_time"] = backtest_run.get("end_date") or config.get("end_time")
                    config["range_by"] = "dates"

        session_id = db_manager.create_simulation_session(user_id, config)
        session = SimulatorSession(session_id=session_id, config=config, db=db_manager)

        if payload.mode == "strategy":
            if not payload.strategy_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="strategy_id is required for strategy mode",
                )
            version_id = (
                payload.strategy_version_id
                if payload.strategy_version_id
                else resolve_strategy_version_id(db_manager, payload.strategy_id)
            )
            strategy_class = load_strategy_class(
                db_manager,
                user_id,
                payload.strategy_id,
                version_id,
            )
            if len(session.symbols) > 1:
                strategies_by_symbol = {}
                for symbol in session.symbols:
                    params = dict(payload.strategy_params or {})
                    params["symbol"] = symbol
                    strategies_by_symbol[symbol] = strategy_class(params=params)
                session.set_strategy_map(strategies_by_symbol)
            else:
                params = dict(payload.strategy_params or {})
                params.setdefault("symbol", config.get("symbol"))
                strategy_instance = strategy_class(params=params)
                session.set_strategy(strategy_instance)

        if payload.mode == "replay" and payload.replay_backtest_id:
            snapshot = db_manager.get_backtest_snapshot(payload.replay_backtest_id)
            trades = (snapshot or {}).get("result", {}).get("trades", [])
            session.set_replay_trades(trades)

        session.load_historical_bars()
        session.apply_mt5_account_defaults()
        session.refresh_risk_state()
        session.ensure_risk_run()
        db_manager.update_simulation_session(
            session_id,
            total_bars=session.total_bars,
            status="running",
            speed_multiplier=payload.speed_multiplier,
            current_bar_index=session.current_bar_index,
        )

        session_coordinator.attach_runtime(session_id, session)
        credentials = db_manager.get_mt5_credentials(user_id) or {}
        company = ""
        try:
            account_info = session.engine.client.account_info()
            if account_info is not None:
                row = account_info._asdict() if hasattr(account_info, "_asdict") else {}
                company = str(row.get("company") or "")
        except Exception:
            company = ""
        return {
            "session_id": session_id,
            "status": "running",
            "total_bars": session.visible_total_steps(),
            "symbol_digits": session.symbol_digits,
            "risk_run_id": session.risk_run_id,
            "config": config,
            "account_leverage": session.engine.account_info().get("leverage"),
            "account_login": credentials.get("login"),
            "account_server": credentials.get("server"),
            "account_company": company or None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to start simulator session: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get("/sessions")
async def list_sessions(user_id: Annotated[int, Depends(_get_authenticated_user_id)]):
    """List sessions for the authenticated user."""
    return db_manager.list_simulation_sessions(user_id=user_id)


@router.get("/paused")
async def list_paused_sessions(
    user_id: Annotated[int, Depends(_get_authenticated_user_id)]
):
    """List paused sessions for resume."""
    return db_manager.get_paused_simulation_sessions(user_id=user_id)


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    session: Annotated[Dict[str, Any], Depends(_get_owned_session)],
):
    """Get a simulation session."""
    return session


@router.put("/{session_id}")
async def update_session(  # noqa: C901
    session_id: int,
    payload: SimulationUpdateRequest,
    session: Annotated[Dict[str, Any], Depends(_get_owned_session)],
):
    """Update speed or pause state."""
    active = session_coordinator.get_runtime(session_id, renew=True)
    if payload.speed_multiplier is not None:
        db_manager.update_simulation_session(
            session_id, speed_multiplier=payload.speed_multiplier
        )
        if active:
            active.speed_multiplier = float(payload.speed_multiplier)

    if payload.paused is not None and active:
        if payload.paused:
            active.pause()
        else:
            active.resume()

    indicator_updates = {}
    if payload.indicators_enabled is not None:
        indicator_updates["indicators_enabled"] = payload.indicators_enabled
    if payload.indicator_sma_enabled is not None:
        indicator_updates["indicator_sma_enabled"] = payload.indicator_sma_enabled
    if payload.indicator_ema_enabled is not None:
        indicator_updates["indicator_ema_enabled"] = payload.indicator_ema_enabled
    if payload.indicator_rsi_enabled is not None:
        indicator_updates["indicator_rsi_enabled"] = payload.indicator_rsi_enabled

    if indicator_updates:
        session_config = dict(session.get("config") or {})
        session_config.update(indicator_updates)
        db_manager.update_simulation_session(session_id, config=session_config)
        if active:
            active.config.update(indicator_updates)

    return {"session_id": session_id, "status": "updated"}


@router.get("/{session_id}/bar/{bar_index}")
async def get_bar(
    session_id: int,
    bar_index: int,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Get a specific bar by index."""
    bar = active.get_bar(bar_index)
    if bar is None:
        raise HTTPException(status_code=404, detail="Bar not found")

    # Process bar through simulator for account updates
    account = active.process_bar_at_index(bar_index)
    indicators = active.get_indicators_at_index(bar_index)
    refresh_session_risk_state(active)

    return {
        "bar": bar,
        "index": bar_index,
        "total_bars": active.visible_total_steps(),
        "digits": active.symbol_digits,
        "account": account,
        "indicators": indicators,
        "completed": active.visible_current_step() >= max(active.visible_total_steps() - 1, 0),
    }


@router.post("/{session_id}/advance")
async def advance_bars(
    session_id: int,
    payload: AdvanceRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Advance the simulation by N bars and return them."""
    bars = active.advance_frames(payload.count)

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)
    refresh_session_risk_state(active)

    positions, orders = collect_positions_orders(active)

    return {
        "bars": bars,
        "current_index": active.visible_current_step(),
        "total_bars": active.visible_total_steps(),
        "digits": active.symbol_digits,
        "completed": active.current_bar_index >= active.total_bars,
        "positions": positions,
        "orders": orders,
        "market": active.get_market_snapshots(),
        "risk_snapshot": active.get_risk_summary(),
        "risk_scorecard": active.get_risk_score_summary(),
        "recommendations": active.get_recommendation_summary(),
        "governance": active.get_governance_report(),
        "trades": active.replay_trades or [],
    }


@router.get("/{session_id}/positions")
async def get_positions(
    session_id: int,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Get current positions and orders for a session."""
    response = build_session_state_response(active)

    return {
        **response,
        "account": {
            "balance": float(active.simulator._account_data.balance),
            "equity": float(active.simulator._account_data.equity),
            "margin": float(active.simulator._account_data.margin),
            "profit": float(active.simulator._account_data.profit),
            "margin_free": float(active.simulator._account_data.margin_free),
            "margin_level": float(active.simulator._account_data.margin_level),
        },
    }


@router.post("/{session_id}/trade")
async def execute_trade(
    session_id: int,
    payload: ManualTradeRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Execute a manual trade within a session."""
    return execute_trade_runtime(active, payload.model_dump())


@router.post("/{session_id}/trade/preview")
async def preview_trade(
    session_id: int,
    payload: ManualTradeRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Preview a manual trade without executing it."""
    return preview_trade_runtime(active, payload.model_dump())


@router.post("/{session_id}/order/pending")
async def place_pending_order(
    session_id: int,
    payload: PendingOrderRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Place a pending order within a session."""
    return place_pending_order_runtime(active, payload.model_dump())


@router.post("/{session_id}/what-if")
async def evaluate_what_if(
    session_id: int,
    payload: WhatIfRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Evaluate a hypothetical portfolio change without mutating the live simulator."""
    return evaluate_what_if_runtime(
        active,
        payload.actions,
        payload.leverage_override,
        refresh_session_risk_state=refresh_session_risk_state,
    )


@router.patch("/{session_id}/positions/{position_id}")
async def modify_position(
    session_id: int,
    position_id: int,
    payload: PositionModifyRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Modify a position's SL/TP."""
    try:
        return modify_position_runtime(
            active,
            session_id=session_id,
            position_id=position_id,
            sl=payload.sl,
            tp=payload.tp,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Modify position error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to modify position")


@router.delete("/{session_id}/positions/{position_id}")
async def close_position(
    session_id: int,
    position_id: int,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Close a position."""
    try:
        return close_position_runtime(
            active,
            session_id=session_id,
            position_id=position_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Close position error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")


@router.post("/{session_id}/positions/{position_id}/partial")
async def partial_close_position(
    session_id: int,
    position_id: int,
    request: Request,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Partially close a position by the given volume."""
    try:
        body = await request.json()
        return partial_close_position_runtime(
            active,
            session_id=session_id,
            position_id=position_id,
            volume=float(body.get("volume", 0.0) or 0.0),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Partial close error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")


@router.patch("/{session_id}/orders/{order_id}")
async def modify_order(
    session_id: int,
    order_id: int,
    payload: OrderModifyRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Modify a pending order's price/SL/TP and optionally reduce its volume."""
    try:
        return modify_order_runtime(
            active,
            session_id=session_id,
            order_id=order_id,
            request_payload=payload.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Modify order error | session={session_id} order={order_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to modify order")


@router.delete("/{session_id}/orders/{order_id}")
async def delete_order(
    session_id: int,
    order_id: int,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Delete a pending order."""
    try:
        return delete_order_runtime(
            active,
            session_id=session_id,
            order_id=order_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Delete order error | session={session_id} order={order_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to delete order")


@router.post("/{session_id}/resume")
async def resume_session(
    session_id: int,
    user_id: Annotated[int, Depends(_get_authenticated_user_id)],
    session_data: Annotated[Dict[str, Any], Depends(_get_owned_session)],
):
    """Resume a paused session."""
    return resume_or_restore_session(
        db_manager=db_manager,
        coordinator=session_coordinator,
        session_id=session_id,
        session_data=session_data,
        user_id=user_id,
    )


@router.post("/{session_id}/seek")
async def seek_session(
    session_id: int,
    payload: SeekRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Seek to a bar index."""
    target_bar_index = active.resolve_base_bar_index(payload.target_time, payload.bar_index)
    active.seek_to_bar(target_bar_index)
    if active.current_bar_index < active.total_bars:
        active.process_bar_at_index(active.current_bar_index)
        refresh_session_risk_state(active)
    return {"session_id": session_id, "bar_index": active.visible_current_step()}


@router.get("/{session_id}/trades")
async def get_session_trades(
    session_id: int,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Get the list of trades (for replay mode)."""
    return active.replay_trades or []


@router.post("/{session_id}/seek-trade")
async def seek_trade(
    session_id: int,
    payload: SeekTradeRequest,
    active: Annotated[SimulatorSession, Depends(_get_running_session)],
):
    """Seek to a specific trade in replay mode."""
    active.seek_to_trade(payload.trade_index)
    return {"session_id": session_id, "bar_index": active.visible_current_step()}


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    _session: Annotated[Dict[str, Any], Depends(_get_owned_session)],
):
    """Delete a session."""
    return delete_session_runtime(
        db_manager=db_manager,
        coordinator=session_coordinator,
        session_id=session_id,
    )


@router.post("/{session_id}/stop-and-save")
async def stop_and_save_session(
    session_id: int,
    user_id: Annotated[int, Depends(_get_authenticated_user_id)],
    _session: Annotated[Dict[str, Any], Depends(_get_owned_session)],
):
    """Stop a simulation session and persist it as a completed backtest run."""
    return stop_and_save_session_runtime(
        db_manager=db_manager,
        coordinator=session_coordinator,
        session_id=session_id,
        user_id=user_id,
    )
