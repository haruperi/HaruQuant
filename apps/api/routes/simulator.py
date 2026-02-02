"""Trading simulator API routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.auth_utils import get_user_id_from_token
from apps.logger import logger
from apps.mt5 import get_mt5_api
from apps.simulation.session import SimulatorSession
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)
mt5 = get_mt5_api()


def _normalize_position(position: dict) -> dict:
    pos_type = position.get("type")
    is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
    return {
        "id": int(
            position.get("id")
            or position.get("ticket")
            or position.get("identifier")
            or 0
        ),
        "symbol": position.get("symbol", ""),
        "type": "buy" if is_buy else "sell",
        "volume": float(position.get("volume") or 0.0),
        "open_price": float(position.get("price_open") or 0.0),
        "price": float(
            position.get("price_current") or position.get("price_open") or 0.0
        ),
        "sl": float(position.get("sl") or 0.0),
        "tp": float(position.get("tp") or 0.0),
        "profit": float(position.get("profit") or 0.0),
        "swap": float(position.get("swap") or 0.0),
        "commission": float(position.get("commission") or 0.0),
        "time": position.get("time"),
        "comment": position.get("comment", ""),
    }


def _normalize_order(order: dict) -> dict:
    type_map = {
        mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
        mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
        mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy_stop_limit",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell_stop_limit",
    }
    order_type = order.get("type")
    return {
        "id": int(
            order.get("ticket") or order.get("identifier") or order.get("id") or 0
        ),
        "symbol": order.get("symbol", ""),
        "type": type_map.get(order_type, str(order_type)),
        "volume": float(
            order.get("volume_current") or order.get("volume_initial") or 0.0
        ),
        "open_price": float(order.get("open_price") or order.get("price_open") or 0.0),
        "sl": float(order.get("sl") or 0.0),
        "tp": float(order.get("tp") or 0.0),
        "time": order.get("time"),
        "expiry_date": order.get("expiry_date"),
        "comment": order.get("comment", ""),
    }


# session_id -> SimulatorSession
active_sessions: Dict[int, SimulatorSession] = {}


class SimulationStartRequest(BaseModel):
    """Request to start a simulation session."""

    session_name: Optional[str] = None
    symbol: str
    timeframe: str = "M1"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    number_of_bars: Optional[int] = None
    initial_balance: float = 10000.0
    speed_multiplier: float = 1.0
    mode: str = Field(default="manual", description="manual | strategy | replay")

    strategy_id: Optional[int] = None
    strategy_version_id: Optional[int] = None
    strategy_params: Optional[Dict[str, Any]] = None

    replay_source: Optional[str] = None  # backtest | csv
    replay_backtest_id: Optional[int] = None
    replay_file_name: Optional[str] = None

    sma_period: Optional[int] = 14
    ema_period: Optional[int] = 14
    rsi_period: Optional[int] = 14
    indicators_enabled: bool = False
    indicator_sma_enabled: bool = False
    indicator_ema_enabled: bool = False
    indicator_rsi_enabled: bool = False


class SimulationUpdateRequest(BaseModel):
    """Request to update a simulation session."""

    speed_multiplier: Optional[float] = None
    paused: Optional[bool] = None
    indicators_enabled: Optional[bool] = None
    indicator_sma_enabled: Optional[bool] = None
    indicator_ema_enabled: Optional[bool] = None
    indicator_rsi_enabled: Optional[bool] = None


class ManualTradeRequest(BaseModel):
    """Request to execute a manual trade."""

    side: str = Field(..., description="buy | sell")
    volume: float = 0.1
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None


class PendingOrderRequest(BaseModel):
    """Request to place a pending order."""

    type: str = Field(
        ...,
        description="buy_limit | sell_limit | buy_stop | sell_stop | buy_stop_limit | sell_stop_limit",
    )
    volume: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None
    expiry_date: Optional[str] = None
    expiration_mode: Optional[str] = "gtc"


class PositionModifyRequest(BaseModel):
    """Request to modify a position."""

    sl: Optional[float] = None
    tp: Optional[float] = None


class OrderModifyRequest(BaseModel):
    """Request to modify a pending order."""

    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class SeekRequest(BaseModel):
    """Request to seek to a bar index."""

    bar_index: int


class AdvanceRequest(BaseModel):
    """Request to advance by N bars."""

    count: int = 1


def _load_strategy_class(user_id: int, strategy_id: int, version_id: int):
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    if version is None:
        raise ValueError(f"Strategy version {version_id} not found")
    if strategy is None:
        raise ValueError(f"Strategy {strategy_id} not found")

    user = db_manager.get_user(user_id=user_id)
    username = (user.get("username") if user else "") or ""
    strategy_name = (strategy.get("name") if strategy else "") or ""

    strategy_class = storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )
    return strategy_class


def _resolve_strategy_version_id(strategy_id: int) -> int:
    strategy = db_manager.get_strategy(strategy_id)
    if not strategy or not strategy.get("active_version_id"):
        raise ValueError("Strategy or active version not found")
    return int(strategy["active_version_id"])


@router.post("/start")
async def start_simulation(
    request: SimulationStartRequest, authorization: str = AUTH_HEADER
):
    """Start a new simulation session."""
    try:
        user_id = get_user_id_from_token(authorization)
        config = request.dict()
        config["user_id"] = user_id

        session_id = db_manager.create_simulation_session(user_id, config)
        session = SimulatorSession(session_id=session_id, config=config, db=db_manager)

        if request.mode == "strategy":
            if not request.strategy_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="strategy_id is required for strategy mode",
                )
            version_id = (
                request.strategy_version_id
                if request.strategy_version_id
                else _resolve_strategy_version_id(request.strategy_id)
            )
            strategy_class = _load_strategy_class(
                user_id, request.strategy_id, version_id
            )
            params = request.strategy_params or {}
            params.setdefault("symbol", request.symbol)
            strategy_instance = strategy_class(params=params)
            session.set_strategy(strategy_instance)

        if request.mode == "replay":
            if request.replay_source == "csv" and not request.replay_backtest_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Import CSV via /api/import/sqx and provide replay_backtest_id",
                )
            if request.replay_backtest_id:
                trades = db_manager.get_backtest_trades(request.replay_backtest_id)
                session.set_replay_trades(trades)

        session.load_historical_bars()
        db_manager.update_simulation_session(
            session_id,
            total_bars=session.total_bars,
            status="running",
            speed_multiplier=request.speed_multiplier,
        )

        active_sessions[session_id] = session
        return {
            "session_id": session_id,
            "status": "running",
            "total_bars": session.total_bars,
            "symbol_digits": session.symbol_digits,
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
async def list_sessions(authorization: str = AUTH_HEADER):
    """List sessions for the authenticated user."""
    user_id = get_user_id_from_token(authorization)
    return db_manager.list_simulation_sessions(user_id=user_id)


@router.get("/paused")
async def list_paused_sessions(authorization: str = AUTH_HEADER):
    """List paused sessions for resume."""
    user_id = get_user_id_from_token(authorization)
    return db_manager.get_paused_simulation_sessions(user_id=user_id)


@router.get("/{session_id}")
async def get_session(session_id: int, authorization: str = AUTH_HEADER):
    """Get a simulation session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/{session_id}")
async def update_session(  # noqa: C901
    session_id: int, request: SimulationUpdateRequest, authorization: str = AUTH_HEADER
):
    """Update speed or pause state."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if request.speed_multiplier is not None:
        db_manager.update_simulation_session(
            session_id, speed_multiplier=request.speed_multiplier
        )
        if active:
            active.speed_multiplier = float(request.speed_multiplier)

    if request.paused is not None and active:
        if request.paused:
            active.pause()
        else:
            active.resume()

    indicator_updates = {}
    if request.indicators_enabled is not None:
        indicator_updates["indicators_enabled"] = request.indicators_enabled
    if request.indicator_sma_enabled is not None:
        indicator_updates["indicator_sma_enabled"] = request.indicator_sma_enabled
    if request.indicator_ema_enabled is not None:
        indicator_updates["indicator_ema_enabled"] = request.indicator_ema_enabled
    if request.indicator_rsi_enabled is not None:
        indicator_updates["indicator_rsi_enabled"] = request.indicator_rsi_enabled

    if indicator_updates:
        session_config = dict(session.get("config") or {})
        session_config.update(indicator_updates)
        db_manager.update_simulation_session(session_id, config=session_config)
        if active:
            active.config.update(indicator_updates)

    return {"session_id": session_id, "status": "updated"}


@router.get("/{session_id}/bar/{bar_index}")
async def get_bar(session_id: int, bar_index: int, authorization: str = AUTH_HEADER):
    """Get a specific bar by index."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    bar = active.get_bar(bar_index)
    if bar is None:
        raise HTTPException(status_code=404, detail="Bar not found")

    # Process bar through simulator for account updates
    account = active.process_bar_at_index(bar_index)
    indicators = active.get_indicators_at_index(bar_index)

    return {
        "bar": bar,
        "index": bar_index,
        "total_bars": active.total_bars,
        "digits": active.symbol_digits,
        "account": account,
        "indicators": indicators,
        "completed": bar_index >= active.total_bars - 1,
    }


@router.post("/{session_id}/advance")
async def advance_bars(
    session_id: int, request: AdvanceRequest, authorization: str = AUTH_HEADER
):
    """Advance the simulation by N bars and return them."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    bars = []
    # current bar index tracked on the session
    for _ in range(request.count):
        if active.current_bar_index >= active.total_bars:
            break
        bar = active.get_bar(active.current_bar_index)
        if bar:
            account = active.process_bar_at_index(active.current_bar_index)
            indicators = active.get_indicators_at_index(active.current_bar_index)
            bars.append(
                {
                    "bar": bar,
                    "index": active.current_bar_index,
                    "account": account,
                    "indicators": indicators,
                }
            )
            active.current_bar_index += 1
            active.save_state()

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)

    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []

    positions = []
    for pos in positions_raw:
        data = pos._asdict() if hasattr(pos, "_asdict") else dict(pos)
        positions.append(_normalize_position(data))

    orders = []
    for order in orders_raw:
        data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        orders.append(_normalize_order(data))

    return {
        "bars": bars,
        "current_index": active.current_bar_index,
        "total_bars": active.total_bars,
        "digits": active.symbol_digits,
        "completed": active.current_bar_index >= active.total_bars,
        "positions": positions,
        "orders": orders,
    }


@router.get("/{session_id}/positions")
async def get_positions(session_id: int, authorization: str = AUTH_HEADER):
    """Get current positions and orders for a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)

    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []

    positions = []
    for pos in positions_raw:
        data = pos._asdict() if hasattr(pos, "_asdict") else dict(pos)
        positions.append(_normalize_position(data))

    orders = []
    for order in orders_raw:
        data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        orders.append(_normalize_order(data))

    return {
        "positions": positions,
        "orders": orders,
        "account": {
            "balance": float(active.simulator._account_data.balance),
            "equity": float(active.simulator._account_data.equity),
            "margin": float(active.simulator._account_data.margin),
            "profit": float(active.simulator._account_data.profit),
            "margin_free": float(active.simulator._account_data.margin_free),
        },
    }


@router.post("/{session_id}/trade")
async def execute_trade(
    session_id: int, request: ManualTradeRequest, authorization: str = AUTH_HEADER
):
    """Execute a manual trade within a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    trade = active.execute_trade(request.dict())
    if not trade:
        raise HTTPException(status_code=500, detail="Trade execution failed")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)

    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []

    positions = []
    for pos in positions_raw:
        data = pos._asdict() if hasattr(pos, "_asdict") else dict(pos)
        positions.append(_normalize_position(data))

    orders = []
    for order in orders_raw:
        data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        orders.append(_normalize_order(data))

    # Return updated positions and orders
    return {
        "trade": trade,
        "positions": positions,
        "orders": orders,
    }


@router.post("/{session_id}/order/pending")
async def place_pending_order(
    session_id: int, request: PendingOrderRequest, authorization: str = AUTH_HEADER
):
    """Place a pending order within a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    order = active.place_pending_order(request.dict())
    if not order:
        raise HTTPException(status_code=500, detail="Pending order failed")

    totals = active.simulator.monitor_positions()
    active.simulator.monitor_account(totals)

    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []

    positions = []
    for pos in positions_raw:
        data = pos._asdict() if hasattr(pos, "_asdict") else dict(pos)
        positions.append(_normalize_position(data))

    orders = []
    for order_row in orders_raw:
        data = order_row._asdict() if hasattr(order_row, "_asdict") else dict(order_row)
        orders.append(_normalize_order(data))

    return {
        "order": order,
        "positions": positions,
        "orders": orders,
    }


@router.patch("/{session_id}/positions/{position_id}")
async def modify_position(
    session_id: int,
    position_id: int,
    request: PositionModifyRequest,
    authorization: str = AUTH_HEADER,
):
    """Modify a position's SL/TP."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Modify position request | session={session_id} position={position_id} "
            f"sl={request.sl} tp={request.tp}"
        )

        pos = active.simulator._positions_data.get(int(position_id))
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_data = pos._asdict() if hasattr(pos, "_asdict") else asdict(pos)
        ok = active.simulator.modify_position(
            pos_data,
            new_sl=request.sl,
            new_tp=request.tp,
        )
        if not ok:
            logger.error(
                f"Modify position failed | session={session_id} position={position_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to modify position")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)

        positions_raw = active.simulator._simulator.positions_get() or []
        orders_raw = active.simulator._simulator.orders_get() or []

        positions = []
        for pos_row in positions_raw:
            data = pos_row._asdict() if hasattr(pos_row, "_asdict") else dict(pos_row)
            positions.append(_normalize_position(data))

        orders = []
        for order_row in orders_raw:
            data = (
                order_row._asdict()
                if hasattr(order_row, "_asdict")
                else dict(order_row)
            )
            orders.append(_normalize_order(data))

        return {"positions": positions, "orders": orders}
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
    authorization: str = AUTH_HEADER,
):
    """Close a position."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Close position request | session={session_id} position={position_id}"
        )

        pos = active.simulator._positions_data.get(int(position_id))
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")

        pos_data = pos._asdict() if hasattr(pos, "_asdict") else asdict(pos)
        ok = active.simulator.close_position(pos_data, reason="manual")
        if not ok:
            logger.error(
                f"Close position failed | session={session_id} position={position_id}"
            )
            raise HTTPException(status_code=500, detail="Failed to close position")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)

        positions_raw = active.simulator._simulator.positions_get() or []
        orders_raw = active.simulator._simulator.orders_get() or []

        positions = []
        for pos_row in positions_raw:
            data = pos_row._asdict() if hasattr(pos_row, "_asdict") else dict(pos_row)
            positions.append(_normalize_position(data))

        orders = []
        for order_row in orders_raw:
            data = (
                order_row._asdict()
                if hasattr(order_row, "_asdict")
                else dict(order_row)
            )
            orders.append(_normalize_order(data))

        return {"positions": positions, "orders": orders}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Close position error | session={session_id} position={position_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to close position")


@router.patch("/{session_id}/orders/{order_id}")
async def modify_order(
    session_id: int,
    order_id: int,
    request: OrderModifyRequest,
    authorization: str = AUTH_HEADER,
):
    """Modify a pending order's price/SL/TP."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(
            f"Modify order request | session={session_id} order={order_id} "
            f"price={request.price} sl={request.sl} tp={request.tp}"
        )

        order = active.simulator._simulator._orders_data.get(int(order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        new_price = (
            request.price if request.price is not None else order_data.get("open_price")
        )
        ok = active.simulator.order_modify(
            order_data,
            new_open_price=float(new_price or 0.0),
            new_sl=float(request.sl or order_data.get("sl") or 0.0),
            new_tp=float(request.tp or order_data.get("tp") or 0.0),
        )
        if not ok:
            logger.error(f"Modify order failed | session={session_id} order={order_id}")
            raise HTTPException(status_code=500, detail="Failed to modify order")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)

        positions_raw = active.simulator._simulator.positions_get() or []
        orders_raw = active.simulator._simulator.orders_get() or []

        positions = []
        for pos_row in positions_raw:
            data = pos_row._asdict() if hasattr(pos_row, "_asdict") else dict(pos_row)
            positions.append(_normalize_position(data))

        orders = []
        for order_row in orders_raw:
            data = (
                order_row._asdict()
                if hasattr(order_row, "_asdict")
                else dict(order_row)
            )
            orders.append(_normalize_order(data))

        return {"positions": positions, "orders": orders}
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
    authorization: str = AUTH_HEADER,
):
    """Delete a pending order."""
    try:
        user_id = get_user_id_from_token(authorization)
        session = db_manager.get_simulation_session(session_id)
        if not session or session.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        active = active_sessions.get(session_id)
        if not active:
            raise HTTPException(status_code=400, detail="Session is not running")

        logger.info(f"Delete order request | session={session_id} order={order_id}")

        order = active.simulator._simulator._orders_data.get(int(order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order_data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        ok = active.simulator.order_delete(order_data)
        if not ok:
            logger.error(f"Delete order failed | session={session_id} order={order_id}")
            raise HTTPException(status_code=500, detail="Failed to delete order")

        totals = active.simulator.monitor_positions()
        active.simulator.monitor_account(totals)

        positions_raw = active.simulator._simulator.positions_get() or []
        orders_raw = active.simulator._simulator.orders_get() or []

        positions = []
        for pos_row in positions_raw:
            data = pos_row._asdict() if hasattr(pos_row, "_asdict") else dict(pos_row)
            positions.append(_normalize_position(data))

        orders = []
        for order_row in orders_raw:
            data = (
                order_row._asdict()
                if hasattr(order_row, "_asdict")
                else dict(order_row)
            )
            orders.append(_normalize_order(data))

        return {"positions": positions, "orders": orders}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Delete order error | session={session_id} order={order_id} err={exc}"
        )
        raise HTTPException(status_code=500, detail="Failed to delete order")


@router.post("/{session_id}/resume")
async def resume_session(session_id: int, authorization: str = AUTH_HEADER):
    """Resume a paused session."""
    user_id = get_user_id_from_token(authorization)
    session_data = db_manager.get_simulation_session(session_id)
    if not session_data or session_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if active:
        active.resume()
        return {"session_id": session_id, "status": "running"}

    config = session_data.get("config") or {}
    config["user_id"] = user_id
    config["current_bar_index"] = session_data.get("current_bar_index", 0)
    config["status"] = "running"

    session = SimulatorSession(session_id=session_id, config=config, db=db_manager)
    session.load_historical_bars()
    active_sessions[session_id] = session
    db_manager.update_simulation_session(session_id, status="running")

    return {"session_id": session_id, "status": "running"}


@router.post("/{session_id}/seek")
async def seek_session(
    session_id: int, request: SeekRequest, authorization: str = AUTH_HEADER
):
    """Seek to a bar index."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.get(session_id)
    if not active:
        raise HTTPException(status_code=400, detail="Session is not running")

    active.seek_to_bar(request.bar_index)
    return {"session_id": session_id, "bar_index": active.current_bar_index}


@router.delete("/{session_id}")
async def delete_session(session_id: int, authorization: str = AUTH_HEADER):
    """Delete a session."""
    user_id = get_user_id_from_token(authorization)
    session = db_manager.get_simulation_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    active = active_sessions.pop(session_id, None)
    if active:
        active.stop()

    db_manager.delete_simulation_session(session_id)
    return {"session_id": session_id, "status": "deleted"}
