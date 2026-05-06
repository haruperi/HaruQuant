"""

Live Trading API Routes.

Provides REST API endpoints for managing live trading sessions, including:

- Session management (CRUD operations)

- Session control (start, stop, pause, resume)

- Strategy management

- Real-time monitoring (signals, positions, logs, statistics)

- Manual trading operations

- Risk rules management

"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import pandas as pd
from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from api.auth_utils import get_user_id_from_token
from api.routes.dashboard.broker import client as global_mt5_client
from api.websocket import live_trading_manager
from haruquant.execution import LiveTradingSession
from haruquant.utils import logger
from services.data.mt5 import get_mt5_api
from haruquant.data import MT5Client
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import StrategyPermissionError, assert_strategy_allowed

mt5 = get_mt5_api()


class MT5Utils:
    @staticmethod
    def add_pips_to_price(price: float, pips: float, symbol_info, direction: int = 1) -> float:
        digits = int(getattr(symbol_info, "digits", 5) or 5)
        pip_size = 0.01 if digits in {2, 3} else 0.0001
        return round(float(price) + (float(direction) * float(pips) * pip_size), digits)


def _fetch_ohlc_data(
    client: MT5Client, symbol: str, timeframe: str, count: int = 500
) -> Optional[pd.DataFrame]:
    """Fetch OHLC data for a symbol from MT5."""
    # Timeframe mapping

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

    mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M1)

    # Fetch rates

    try:

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)

        if rates is None:

            return None

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(df["time"], unit="s")

        return df

    except Exception as e:

        logger.error(f"Error fetching OHLC data: {e}")

        return None


def _ensure_mt5_connection(user_id: int) -> MT5Client:
    """Ensure global MT5 client is configured and connected for the user."""
    # Check if already connected with correct login

    # For simplicity, we'll fetch creds and ensure configuration matches

    creds = db_manager.get_mt5_credentials(user_id) or {}

    login = creds.get("login")

    password = creds.get("password")

    server = creds.get("server")

    path = creds.get("path", "")

    if not login or not password or not server:

        logger.warning("MT5 credentials missing; cannot connect")

        return global_mt5_client

    try:

        login_int = int(login)

    except (ValueError, TypeError):

        login_int = 0

    # Configure client

    global_mt5_client.account_login = login_int  # type: ignore[attr-defined]
    global_mt5_client.account_password = password  # type: ignore[attr-defined]
    global_mt5_client.account_server = server  # type: ignore[attr-defined]

    if path:

        global_mt5_client.path = path  # type: ignore[attr-defined]

    # Initialize

    if not global_mt5_client.connect(
        path=path,
        login=login_int,
        password=password,
        server=server,
    ):

        logger.error("Failed to initialize MT5 client with user credentials")

    return global_mt5_client


router = APIRouter()

db_manager = DatabaseManager()

AUTH_HEADER = Header(None)

SESSION_STATUS_FILTER_QUERY = Query(None, description="Filter by status")

CANDLES_SYMBOL_QUERY = Query(..., description="Trading symbol (e.g., XAUUSD)")

CANDLES_TIMEFRAME_QUERY = Query(..., description="Timeframe (e.g., M1, M15, H1)")

CANDLES_COUNT_QUERY = Query(500, description="Number of candles to fetch")

SIGNALS_LIMIT_QUERY = Query(50, description="Maximum number of signals to return")

SIGNALS_STATUS_QUERY = Query(None, description="Filter by status")

POSITIONS_STATUS_QUERY = Query(None, description="Filter by status")

LOGS_LIMIT_QUERY = Query(100, description="Maximum number of logs to return")

LOGS_LEVEL_QUERY = Query(None, description="Filter by log level")

LOGS_CATEGORY_QUERY = Query(None, description="Filter by category")

# Global dictionary to store active live trading sessions

# session_id -> LiveTradingSession instance

active_sessions: Dict[int, LiveTradingSession] = {}


def _get_active_session(session_id: int, user_id: int, action: str):

    session = db_manager.get_live_session(session_id)

    if not session:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session["user_id"] != user_id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this session",
        )

    if session_id not in active_sessions:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session must be running to {action}",
        )

    return session, active_sessions[session_id]


def _get_symbol_info(symbol: str):

    info = mt5.symbol_info_tick(symbol)

    if info is None:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data unavailable for {symbol}",
        )

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Symbol info unavailable for {symbol}",
        )

    return info, symbol_info


def _get_entry_price_and_direction(order_type: str, info):

    if order_type.lower() == "buy":

        return info.ask, -1, 1

    return info.bid, 1, -1


def _calculate_sl_tp(
    entry_price: float,
    sl_pips: Optional[float],
    tp_pips: Optional[float],
    symbol_info,
    direction_sl: int,
    direction_tp: int,
):

    stop_loss = 0.0

    take_profit = 0.0

    if sl_pips is not None and sl_pips > 0:

        stop_loss = MT5Utils.add_pips_to_price(
            entry_price, sl_pips, symbol_info, direction_sl
        )

    if tp_pips is not None and tp_pips > 0:

        take_profit = MT5Utils.add_pips_to_price(
            entry_price, tp_pips, symbol_info, direction_tp
        )

    return stop_loss, take_profit


def _get_session_magic_numbers(session_id: int) -> List[int]:

    strategies = db_manager.get_session_strategies(session_id)

    magics = {0}

    for strat in strategies:

        magic_value = strat.get("magic_number")

        if magic_value is None:

            continue

        try:

            magics.add(int(magic_value))

        except (TypeError, ValueError):

            continue

    return list(magics)


def _normalize_optional_price(value: Optional[float]) -> Optional[float]:

    if value is None:

        return None

    try:

        numeric = float(value)

    except (TypeError, ValueError):

        return None

    return numeric if numeric > 0 else None


def _map_mt5_position(position: Any, session_id: int) -> Dict[str, Any]:

    pos_type_value = getattr(position, "type", None)

    pos_type = "buy" if pos_type_value == 0 else "sell"

    timestamp = getattr(position, "time", None) or getattr(
        position, "time_update", None
    )

    if timestamp:

        open_time = datetime.fromtimestamp(timestamp).isoformat()

    else:

        open_time = datetime.utcnow().isoformat()

    open_price = float(getattr(position, "price_open", 0.0))

    current_price = getattr(position, "price_current", open_price)

    profit = getattr(position, "profit", None)

    volume = float(getattr(position, "volume", 0.0))

    ticket = int(getattr(position, "ticket", 0))

    stop_loss = _normalize_optional_price(getattr(position, "sl", None))

    take_profit = _normalize_optional_price(getattr(position, "tp", None))

    return {
        "position_id": ticket,
        "session_id": session_id,
        "signal_id": None,
        "mt5_ticket": ticket,
        "mt5_order": getattr(position, "order", None),
        "symbol": getattr(position, "symbol", ""),
        "type": pos_type,
        "open_time": open_time,
        "open_price": open_price,
        "position_size": volume,
        "current_price": current_price,
        "current_profit": profit,
        "current_profit_pct": None,
        "initial_stop_loss": stop_loss,
        "current_stop_loss": stop_loss,
        "initial_take_profit": take_profit,
        "current_take_profit": take_profit,
        "breakeven_activated": False,
        "trailing_stop_activated": False,
        "partial_close_count": 0,
        "status": "open",
        "close_reason": None,
        "close_time": None,
        "close_price": None,
        "final_profit": None,
        "final_profit_pct": None,
        "created_at": open_time,
        "updated_at": open_time,
    }


def _map_mt5_order(order: Any) -> Dict[str, Any]:

    type_map = {
        getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2): "buy_limit",
        getattr(mt5, "ORDER_TYPE_SELL_LIMIT", 3): "sell_limit",
        getattr(mt5, "ORDER_TYPE_BUY_STOP", 4): "buy_stop",
        getattr(mt5, "ORDER_TYPE_SELL_STOP", 5): "sell_stop",
        getattr(mt5, "ORDER_TYPE_BUY_STOP_LIMIT", 6): "buy_stop_limit",
        getattr(mt5, "ORDER_TYPE_SELL_STOP_LIMIT", 7): "sell_stop_limit",
    }

    order_type = getattr(order, "type", None)

    return {
        "id": int(
            getattr(order, "ticket", None) or getattr(order, "identifier", None) or 0
        ),
        "symbol": getattr(order, "symbol", ""),
        "type": type_map.get(order_type, str(order_type)),
        "volume": float(
            getattr(order, "volume_current", None)
            or getattr(order, "volume_initial", None)
            or 0.0
        ),
        "open_price": float(
            getattr(order, "price_open", None)
            or getattr(order, "open_price", None)
            or 0.0
        ),
        "sl": float(getattr(order, "sl", None) or 0.0),
        "tp": float(getattr(order, "tp", None) or 0.0),
        "time": getattr(order, "time_setup", None) or getattr(order, "time", None),
        "expiry_date": getattr(order, "time_expiration", None),
        "comment": getattr(order, "comment", "") or "",
    }


def _get_session_for_user(session_id: int, user_id: int) -> Dict[str, Any]:

    session = db_manager.get_live_session(session_id)

    if not session:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session["user_id"] != user_id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this session",
        )

    return session


async def _maybe_auto_stop_session(
    session_id: int, session: Dict[str, Any]
) -> Dict[str, Any]:

    stop_mode = session.get("stop_mode") or "manual"

    stop_at = session.get("stop_at")

    if stop_mode != "auto" or not stop_at or session.get("status") != "running":

        return session

    try:

        stop_at_dt = datetime.fromisoformat(stop_at.replace("Z", ""))

    except ValueError:

        logger.warning(f"Invalid stop_at for session {session_id}: {stop_at}")

        return session

    if datetime.now() < stop_at_dt:

        return session

    if session_id in active_sessions:

        await active_sessions[session_id].stop()

    db_manager.update_live_session(
        session_id,
        status="stopped",
        stopped_at=datetime.now().isoformat(),
    )

    session = db_manager.get_live_session(session_id) or session

    await live_trading_manager.send_status_update(
        session_id,
        {
            "session_id": session["session_id"],
            "session_name": session["session_name"],
            "status": "stopped",
            "running": False,
            "paused": False,
            "stop_mode": session.get("stop_mode"),
            "stop_at": session.get("stop_at"),
            "signals_detected": session.get("total_signals_detected", 0),
            "signals_approved": session.get("total_signals_executed", 0),
            "signals_rejected": session.get("total_signals_rejected", 0),
            "positions_opened": 0,
            "positions_closed": 0,
            "active_positions": 0,
            "current_equity": 0.0,
            "current_balance": 0.0,
            "account_name": None,
            "account_server": None,
            "account_login": None,
        },
    )

    return session


def _get_account_snapshot() -> Dict[str, Any]:

    account_snapshot: Dict[str, Any] = {
        "current_equity": 0.0,
        "current_balance": 0.0,
        "account_name": None,
        "account_server": None,
        "account_login": None,
    }

    if global_mt5_client.is_connected():
        account_info = mt5.account_info()
        if account_info is not None:
            row = account_info._asdict() if hasattr(account_info, "_asdict") else {}
            account_snapshot["current_equity"] = float(row.get("equity", 0.0) or 0.0)
            account_snapshot["current_balance"] = float(row.get("balance", 0.0) or 0.0)
            account_snapshot["account_name"] = row.get("name")
            account_snapshot["account_server"] = row.get("server")
            account_snapshot["account_login"] = row.get("login")

    return account_snapshot


def _get_strategy_removal_labels(
    session_id: int, strategy_config_id: int
) -> Dict[str, str]:

    strategy_name = None

    strategy_version_label = None

    try:

        strategies = db_manager.get_session_strategies(session_id)

        for strategy in strategies:

            if strategy.get("id") == strategy_config_id:

                strategy_name = strategy.get("strategy_name")

                strategy_version_label = strategy.get("version")

                break

    except Exception as exc:

        logger.warning(
            f"Failed to resolve strategy name for removal {strategy_config_id}: {exc}"
        )

    strategy_label = strategy_name or f"config_id={strategy_config_id}"

    version_suffix = f" (v{strategy_version_label})" if strategy_version_label else ""

    return {
        "strategy_label": strategy_label,
        "version_suffix": version_suffix,
    }


def _get_strategy_add_labels(strategy_version_id: int) -> Dict[str, str]:

    strategy_version = db_manager.get_strategy_version(strategy_version_id)

    strategy_name = None

    strategy_version_label = None

    if strategy_version:

        strategy_version_label = strategy_version.get("version")

        strategy_id_value = strategy_version.get("strategy_id")

        if strategy_id_value is not None:

            strategy = db_manager.get_strategy(int(strategy_id_value))

            if strategy:

                strategy_name = strategy.get("name")

    strategy_label = strategy_name or f"version_id={strategy_version_id}"

    version_suffix = f" (v{strategy_version_label})" if strategy_version_label else ""

    return {
        "strategy_label": strategy_label,
        "version_suffix": version_suffix,
    }


async def _close_positions(trading_session, active_positions):

    closed_count = 0

    failed_positions = []

    for position_id, position in list(active_positions.items()):

        try:

            success = await trading_session.execution_engine.close_position(
                position=position, reason="flatten_all"
            )

            if success:

                closed_count += 1

            else:

                failed_positions.append(position_id)

        except Exception as exc:

            logger.error(f"Error closing position {position_id}: {exc}")

            failed_positions.append(position_id)

    return closed_count, failed_positions


# =============================================================================

# Authentication Helper

# =============================================================================

# =============================================================================

# Pydantic Models for Request/Response

# =============================================================================


class SessionCreateRequest(BaseModel):
    """Request model for creating a new live trading session."""

    session_name: str = Field(..., description="Name of the session")

    mode: str = Field(default="paper", description="Trading mode: paper or live")

    stop_mode: str = Field(
        default="manual", description="Session stop mode: manual or auto"
    )

    stop_at: Optional[str] = Field(None, description="Auto stop time (ISO format)")

    max_total_risk_pct: float = Field(
        default=2.0, description="Max % of account at risk"
    )

    max_positions: int = Field(default=5, description="Max concurrent positions")

    max_correlation: float = Field(default=0.7, description="Max allowed correlation")

    max_drawdown_pct: float = Field(
        default=10.0, description="Stop all if DD exceeds this"
    )

    trading_hours_start: Optional[str] = Field(
        None, description="Trading start time (HH:MM)"
    )

    trading_hours_end: Optional[str] = Field(
        None, description="Trading end time (HH:MM)"
    )

    allowed_days: Optional[str] = Field(
        None, description="JSON array of allowed days [1,2,3,4,5]"
    )


class SessionUpdateRequest(BaseModel):
    """Request model for updating a session."""

    session_name: Optional[str] = None

    mode: Optional[str] = None

    stop_mode: Optional[str] = None

    stop_at: Optional[str] = None

    max_total_risk_pct: Optional[float] = None

    max_positions: Optional[int] = None

    max_correlation: Optional[float] = None

    max_drawdown_pct: Optional[float] = None

    trading_hours_start: Optional[str] = None

    trading_hours_end: Optional[str] = None

    allowed_days: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session data."""

    session_id: int

    user_id: int

    session_name: str

    status: str

    mode: str

    stop_mode: Optional[str]

    stop_at: Optional[str]

    max_total_risk_pct: float

    max_positions: int

    max_correlation: float

    max_drawdown_pct: float

    trading_hours_start: Optional[str]

    trading_hours_end: Optional[str]

    allowed_days: Optional[str]

    started_at: Optional[str]

    stopped_at: Optional[str]

    last_heartbeat: Optional[str]

    error_message: Optional[str]

    total_signals_detected: int

    total_signals_executed: int

    total_signals_rejected: int

    created_at: str

    updated_at: str


class SessionStatusResponse(BaseModel):
    """Lightweight response for session status."""

    session_id: int

    session_name: str

    status: str

    running: bool

    paused: bool

    stop_mode: Optional[str] = None

    stop_at: Optional[str] = None

    signals_detected: int

    signals_approved: int

    signals_rejected: int

    positions_opened: int

    positions_closed: int

    active_positions: int

    current_equity: float = 0.0

    current_balance: float = 0.0

    account_name: Optional[str] = None

    account_server: Optional[str] = None

    account_login: Optional[int] = None

    daily_pnl: float = 0.0

    daily_pnl_limit: float = 0.0

    current_drawdown_pct: float = 0.0

    max_drawdown_pct: float = 10.0


class SessionStatisticsResponse(BaseModel):
    """Comprehensive session statistics."""

    session: Dict[str, Any]

    health: Dict[str, Any]

    signals: Dict[str, Any]

    positions: Dict[str, Any]

    signal_engine: Dict[str, Any]

    risk_manager: Dict[str, Any]

    execution_engine: Dict[str, Any]

    trade_manager: Dict[str, Any]


class StrategyAddRequest(BaseModel):
    """Request model for adding a strategy to a session."""

    strategy_version_id: int

    symbols: List[str] = Field(..., description="List of symbols for this strategy")

    timeframes: List[str] = Field(..., description="List of timeframes")

    max_risk_per_trade_pct: float = Field(default=1.0)

    position_size_type: str = Field(
        default="risk", description="risk, fixed, or percent"
    )

    position_size_value: float = Field(default=1.0)

    strategy_params: Optional[Dict[str, Any]] = None


class StrategyUpdateRequest(BaseModel):
    """Request model for updating strategy configuration."""

    is_active: Optional[bool] = None

    symbols: Optional[List[str]] = None

    timeframes: Optional[List[str]] = None

    max_risk_per_trade_pct: Optional[float] = None

    position_size_type: Optional[str] = None

    position_size_value: Optional[float] = None

    strategy_params: Optional[Dict[str, Any]] = None


class PositionModifyRequest(BaseModel):
    """Request model for modifying a position."""

    stop_loss: Optional[float] = None

    take_profit: Optional[float] = None


class ManualOrderRequest(BaseModel):
    """Request model for placing a manual order."""

    symbol: str = Field(..., description="Trading symbol")

    volume: float = Field(..., description="Volume in lots")

    type: str = Field(..., description="Order type: buy or sell")

    sl_pips: Optional[float] = Field(None, description="Stop Loss in pips")

    tp_pips: Optional[float] = Field(None, description="Take Profit in pips")

    comment: Optional[str] = "Manual Order"


class PendingOrderRequest(BaseModel):
    """Request model for placing a pending order."""

    symbol: str = Field(..., description="Trading symbol")

    volume: float = Field(..., description="Volume in lots")

    type: str = Field(
        ..., description="Order type: buy_limit, sell_limit, buy_stop, sell_stop"
    )

    price: float = Field(..., description="Entry price for pending order")

    sl_pips: Optional[float] = Field(None, description="Stop Loss in pips")

    tp_pips: Optional[float] = Field(None, description="Take Profit in pips")

    comment: Optional[str] = "Manual Pending Order"


class SignalResponse(BaseModel):
    """Response model for signal data."""

    signal_id: int

    session_id: int

    strategy_version_id: int

    symbol: str

    timeframe: str

    signal_type: str

    signal_time: str

    entry_price: Optional[float]

    stop_loss: Optional[float]

    take_profit: Optional[float]

    risk_pips: Optional[float]

    risk_usd: Optional[float]

    position_size: Optional[float]

    reward_risk_ratio: Optional[float]

    status: str

    rejection_reason: Optional[str]

    created_at: str


class PositionResponse(BaseModel):
    """Response model for position data."""

    position_id: int

    session_id: int

    signal_id: Optional[int]

    mt5_ticket: Optional[int]

    mt5_order: Optional[int]

    symbol: str

    type: str

    open_time: str

    open_price: float

    position_size: float

    current_price: Optional[float]

    current_profit: Optional[float]

    current_profit_pct: Optional[float]

    initial_stop_loss: Optional[float]

    current_stop_loss: Optional[float]

    initial_take_profit: Optional[float]

    current_take_profit: Optional[float]

    breakeven_activated: bool

    trailing_stop_activated: bool

    partial_close_count: int

    status: str

    close_reason: Optional[str]

    close_time: Optional[str]

    close_price: Optional[float]

    final_profit: Optional[float]

    final_profit_pct: Optional[float]

    created_at: str

    updated_at: str


def _get_session_positions_response(
    session_id: int, status_filter: Optional[str]
) -> List[PositionResponse]:

    if session_id in active_sessions:

        if status_filter and status_filter != "open":

            return []

        trading_session = active_sessions[session_id]

        client = (
            trading_session.engine.client
            if trading_session.engine and trading_session.engine.client
            else trading_session.mt5_client
        )

        positions = client.positions_get() if client else []

        allowed_magics = set(_get_session_magic_numbers(session_id))

        filtered_positions = []

        for pos in positions:

            magic_value = getattr(pos, "magic", None)

            try:

                magic_int = int(magic_value) if magic_value is not None else 0

            except (TypeError, ValueError):

                magic_int = 0

            if magic_int in allowed_magics:

                filtered_positions.append(pos)

        return [
            PositionResponse(**_map_mt5_position(pos, session_id))
            for pos in filtered_positions
        ]

    positions = db_manager.get_session_positions(session_id)

    if status_filter:

        positions = [p for p in positions if p.get("status") == status_filter]

    return [PositionResponse(**position) for position in positions]


# =============================================================================

# Session Management Endpoints

# =============================================================================


@router.post(
    "/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_session(
    request: SessionCreateRequest, authorization: str = AUTH_HEADER
):
    """

    Create a new live trading session.

    Creates a session configuration in the database. The session is created

    in 'stopped' status and must be explicitly started using the start endpoint.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(
            f"Creating live trading session for user {user_id}: {request.session_name}"
        )

        # Create session in database

        session_id = db_manager.create_live_session(
            user_id=user_id,
            session_name=request.session_name,
            mode=request.mode,
            stop_mode=request.stop_mode,
            stop_at=request.stop_at,
            max_total_risk_pct=request.max_total_risk_pct,
            max_positions=request.max_positions,
            max_correlation=request.max_correlation,
            max_drawdown_pct=request.max_drawdown_pct,
            trading_hours_start=request.trading_hours_start,
            trading_hours_end=request.trading_hours_end,
            allowed_days=(
                json.loads(request.allowed_days) if request.allowed_days else None
            ),
        )

        if not session_id:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session",
            )

        # Get the created session

        session = db_manager.get_live_session(session_id)

        logger.info(f"Live trading session created successfully: {session_id}")

        return SessionResponse(**cast(dict, session))

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error creating session: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating session: {str(e)}",
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    authorization: str = AUTH_HEADER,
    status_filter: Optional[str] = SESSION_STATUS_FILTER_QUERY,
):
    """

    List all live trading sessions for the authenticated user.

    Optionally filter by status (stopped, running, paused, error).

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(
            f"Listing sessions for user {user_id}, status_filter={status_filter}"
        )

        sessions = db_manager.get_user_live_sessions(user_id)

        # Apply status filter if provided

        if status_filter:

            sessions = [s for s in sessions if s.get("status") == status_filter]

        logger.info(f"Found {len(sessions)} sessions for user {user_id}")

        return [SessionResponse(**session) for session in sessions]

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error listing sessions: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while listing sessions",
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Get details of a specific live trading session.

    Returns complete session configuration and current state.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Getting session {session_id} for user {user_id}")

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session",
            )

        return SessionResponse(**session)

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving session",
        )


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int, request: SessionUpdateRequest, authorization: str = AUTH_HEADER
):
    """

    Update a live trading session configuration.

    Session must be in 'stopped' status to be updated.

    Only provided fields will be updated.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Updating session {session_id} for user {user_id}")

        # Get existing session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this session",
            )

        # Check session is stopped

        if session["status"] != "stopped":

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be stopped to update configuration",
            )

        # Build update dict (only non-None values)

        update_data = {
            k: v for k, v in request.dict(exclude_unset=True).items() if v is not None
        }

        if not update_data:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
            )

        # Update session

        success = db_manager.update_live_session(session_id, **update_data)

        if not success:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update session",
            )

        # Return updated session

        updated_session = db_manager.get_live_session(session_id)

        logger.info(f"Session {session_id} updated successfully")

        return SessionResponse(**cast(dict, updated_session))

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error updating session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating session",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Delete a live trading session.

    Session must be in 'stopped' status to be deleted.

    This will also delete all associated strategies, signals, positions, and logs.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Deleting session {session_id} for user {user_id}")

        # Get existing session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this session",
            )

        # Check session is stopped

        if session["status"] != "stopped":

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be stopped before deletion",
            )

        # Remove from active sessions if present

        if session_id in active_sessions:

            del active_sessions[session_id]

        # Delete from database (cascades to all related tables)

        success = db_manager.delete_live_session(session_id)

        if not success:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete session",
            )

        logger.info(f"Session {session_id} deleted successfully")

        return None

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error deleting session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting session",
        )


# =============================================================================

# Session Control Endpoints

# =============================================================================


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Start a live trading session.

    Initializes all components (SignalEngine, RiskManager, ExecutionEngine, TradeManager)

    and begins signal detection and position monitoring.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Starting session {session_id} for user {user_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to start this session",
            )

        # Check session is stopped

        if session["status"] not in ["stopped", "error"]:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is already {session['status']}",
            )

        # Check if session already exists

        if session_id in active_sessions:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is already running",
            )

        # Initialize MT5 client

        mt5_client = _ensure_mt5_connection(user_id)

        if not mt5_client.is_connected():

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to initialize MT5 connection",
            )

        # Create LiveTradingSession instance

        trading_session = LiveTradingSession(
            session_id=session_id, mt5_client=mt5_client, db=db_manager
        )

        # Start the session

        await trading_session.start()

        # Store in active sessions

        active_sessions[session_id] = trading_session

        logger.info(f"Session {session_id} started successfully")

        return {
            "message": "Session started successfully",
            "session_id": session_id,
            "status": "running",
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error starting session {session_id}: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while starting session: {str(e)}",
        )


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Stop a live trading session.

    Stops signal detection, stops position monitoring, and updates session status.

    Active positions are left open unless explicitly closed.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Stopping session {session_id} for user {user_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to stop this session",
            )

        # Check if session is running

        if session_id not in active_sessions:

            # Update database status to stopped if needed

            if session["status"] != "stopped":

                db_manager.update_live_session(session_id, status="stopped")

            return {
                "message": "Session is already stopped",
                "session_id": session_id,
                "status": "stopped",
            }

        # Get the trading session instance

        trading_session = active_sessions[session_id]

        # Stop the session

        await trading_session.stop()

        # Remove from active sessions

        del active_sessions[session_id]

        logger.info(f"Session {session_id} stopped successfully")

        return {
            "message": "Session stopped successfully",
            "session_id": session_id,
            "status": "stopped",
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error stopping session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while stopping session: {str(e)}",
        )


@router.post("/sessions/{session_id}/pause")
async def pause_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Pause a live trading session.

    Stops signal detection but continues monitoring active positions.

    New signals will not be detected while paused.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Pausing session {session_id} for user {user_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to pause this session",
            )

        # Check if session is running

        if session_id not in active_sessions:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not running"
            )

        # Get the trading session instance

        trading_session = active_sessions[session_id]

        # Pause the session

        await trading_session.pause()

        logger.info(f"Session {session_id} paused successfully")

        return {
            "message": "Session paused successfully",
            "session_id": session_id,
            "status": "paused",
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error pausing session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while pausing session: {str(e)}",
        )


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: int, authorization: str = AUTH_HEADER):
    """

    Resume a paused live trading session.

    Restarts signal detection while continuing position monitoring.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Resuming session {session_id} for user {user_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to resume this session",
            )

        # Check if session is running

        if session_id not in active_sessions:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not running"
            )

        # Get the trading session instance

        trading_session = active_sessions[session_id]

        # Resume the session

        await trading_session.resume()

        logger.info(f"Session {session_id} resumed successfully")

        return {
            "message": "Session resumed successfully",
            "session_id": session_id,
            "status": "running",
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error resuming session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while resuming session: {str(e)}",
        )


# =============================================================================

# Monitoring Endpoints

# =============================================================================

# Assuming SessionStatusResponse is defined elsewhere and looks something like this:

# class SessionStatusResponse(BaseModel):

#     session_id: int

#     session_name: str

#     status: str

#     running: bool

#     paused: bool

#     signals_detected: int

#     signals_approved: int

#     signals_rejected: int

#     positions_opened: int

#     positions_closed: int

#     active_positions: int

#     current_equity: float = 0.0

#     current_balance: float = 0.0

#     account_name: Optional[str] = None

#     account_server: Optional[str] = None

#     account_login: Optional[int] = None


@router.get("/sessions/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: int, authorization: str = AUTH_HEADER):
    """

    Get lightweight real-time status of a session.

    Returns current status, counts, and key metrics without heavy statistics.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = _get_session_for_user(session_id, user_id)

        session = await _maybe_auto_stop_session(session_id, session)

        # If session is running, get live status

        if session_id in active_sessions:

            trading_session = active_sessions[session_id]

            status_data = trading_session.get_status()

            status_data["stop_mode"] = session.get("stop_mode")

            status_data["stop_at"] = session.get("stop_at")

            return SessionStatusResponse(**status_data)

        account_snapshot = _get_account_snapshot()

        return SessionStatusResponse(
            session_id=session["session_id"],
            session_name=session["session_name"],
            status=session["status"],
            running=False,
            paused=False,
            stop_mode=session.get("stop_mode"),
            stop_at=session.get("stop_at"),
            signals_detected=session.get("total_signals_detected", 0),
            signals_approved=session.get("total_signals_executed", 0),
            signals_rejected=session.get("total_signals_rejected", 0),
            positions_opened=0,
            positions_closed=0,
            active_positions=0,
            current_equity=account_snapshot["current_equity"],
            current_balance=account_snapshot["current_balance"],
            account_name=account_snapshot["account_name"],
            account_server=account_snapshot["account_server"],
            account_login=account_snapshot["account_login"],
        )

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session status {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving session status",
        )


@router.get(
    "/sessions/{session_id}/statistics", response_model=SessionStatisticsResponse
)
async def get_session_statistics(session_id: int, authorization: str = AUTH_HEADER):
    """

    Get comprehensive session statistics.

    Returns detailed statistics from all components (SignalEngine, RiskManager,

    ExecutionEngine, TradeManager) plus session-level metrics.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session",
            )

        # If session is running, get live statistics

        if session_id in active_sessions:

            trading_session = active_sessions[session_id]

            stats = trading_session.get_statistics()

            return SessionStatisticsResponse(**stats)

        # Session is not running, return basic info

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not running - statistics only available for active sessions",
        )

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session statistics {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving session statistics",
        )


@router.get("/sessions/{session_id}/market-data")
async def get_market_data(
    session_id: int,
    symbol: str = CANDLES_SYMBOL_QUERY,
    timeframe: str = CANDLES_TIMEFRAME_QUERY,
    count: int = CANDLES_COUNT_QUERY,
    authorization: str = AUTH_HEADER,
):
    """

    Get historical candlestick data from MT5 for charting.

    Returns OHLC data for the specified symbol and timeframe.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session",
            )

        # Get active session if running

        if session_id in active_sessions:

            trading_session = active_sessions[session_id]

            mt5_client = trading_session.mt5_client

        else:

            # Create temporary MT5 client for data fetching

            mt5_client = _ensure_mt5_connection(user_id)

            if not mt5_client.is_connected():

                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="MT5 connection not available",
                )

        # Fetch OHLC data

        data = _fetch_ohlc_data(
            client=mt5_client, symbol=symbol, timeframe=timeframe, count=count
        )

        if data is None or data.empty:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for {symbol} {timeframe}",
            )

        # Get symbol info for digits

        symbol_info = mt5_client.symbol_info(symbol)
        digits = getattr(symbol_info, "digits", 5) if symbol_info else 5

        # Convert DataFrame to list of dicts for JSON response

        candles = []

        for _, row in data.iterrows():

            candles.append(
                {
                    "time": int(row["time"].timestamp()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row.get("tick_volume", 0)),
                }
            )

        return {"candles": candles, "digits": digits}

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error fetching market data: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching market data",
        )


@router.get("/sessions/{session_id}/signals", response_model=List[SignalResponse])
async def get_session_signals(
    session_id: int,
    authorization: str = AUTH_HEADER,
    limit: int = SIGNALS_LIMIT_QUERY,
    status_filter: Optional[str] = SIGNALS_STATUS_QUERY,
):
    """

    Get detected signals for a session.

    Returns a list of signals with optional status filter (pending, approved, rejected, executed, failed).

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session",
            )

        # Get signals from database

        signals = db_manager.get_session_signals(session_id, limit=limit)

        # Apply status filter if provided

        if status_filter:

            signals = [s for s in signals if s.get("status") == status_filter]

        return [SignalResponse(**signal) for signal in signals]

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session signals {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving signals",
        )


@router.get("/sessions/{session_id}/positions", response_model=List[PositionResponse])
async def get_session_positions(
    session_id: int,
    authorization: str = AUTH_HEADER,
    status_filter: Optional[str] = POSITIONS_STATUS_QUERY,
):
    """

    Get positions for a session.

    Returns a list of positions with optional status filter (open, closed).

    """
    try:

        user_id = get_user_id_from_token(authorization)

        _get_session_for_user(session_id, user_id)

        return _get_session_positions_response(session_id, status_filter)

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session positions {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving positions",
        )


@router.get("/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: int,
    authorization: str = AUTH_HEADER,
    limit: int = LOGS_LIMIT_QUERY,
    level: Optional[str] = LOGS_LEVEL_QUERY,
    category: Optional[str] = LOGS_CATEGORY_QUERY,
):
    """

    Get session logs.

    Returns a list of log messages with optional filtering by level and category.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session",
            )

        # Get logs from database

        logs = db_manager.get_session_logs(
            session_id=session_id,
            limit=limit,
            log_level=level,
            log_category=category,
        )

        return {"logs": logs}

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session logs {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving logs",
        )


# =============================================================================

# Strategy Management Endpoints

# =============================================================================


@router.post("/sessions/{session_id}/strategies")
async def add_strategy_to_session(
    session_id: int, request: StrategyAddRequest, authorization: str = AUTH_HEADER
):
    """

    Add a strategy to a live trading session.

    Session must be stopped to add strategies.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        session = _get_session_for_user(session_id, user_id)

        # Check session is stopped

        if session["status"] != "stopped":

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be stopped to add strategies",
            )

        labels = _get_strategy_add_labels(request.strategy_version_id)

        strategy_label = labels["strategy_label"]

        version_suffix = labels["version_suffix"]

        session_label = session.get("session_name") or f"id={session_id}"

        version = db_manager.get_strategy_version(request.strategy_version_id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy version {request.strategy_version_id} not found",
            )
        assert_strategy_allowed(
            int(version["strategy_id"]),
            "live",
            db_manager=db_manager,
        )

        logger.info(
            f"Adding strategy {strategy_label}{version_suffix} to session {session_label}"
        )

        # Add strategy to session

        strategy_id = db_manager.add_strategy_to_session(
            session_id=session_id,
            strategy_version_id=request.strategy_version_id,
            symbols=request.symbols,
            timeframes=request.timeframes,
            max_risk_per_trade_pct=request.max_risk_per_trade_pct,
            position_size_type=request.position_size_type,
            position_size_value=request.position_size_value,
            strategy_params=request.strategy_params,
        )

        if not strategy_id:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add strategy to session",
            )

        logger.info(
            f"Strategy {strategy_label}{version_suffix} added to session {session_label}"
        )

        return {
            "message": "Strategy added successfully",
            "session_id": session_id,
            "strategy_id": strategy_id,
        }

    except HTTPException:

        raise

    except StrategyPermissionError as e:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e

    except Exception as e:

        logger.error(f"Error adding strategy to session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while adding strategy: {str(e)}",
        )


@router.delete("/sessions/{session_id}/strategies/{strategy_config_id}")
async def remove_strategy_from_session(
    session_id: int, strategy_config_id: int, authorization: str = AUTH_HEADER
):
    """

    Remove a strategy from a live trading session.

    Session must be stopped to remove strategies.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        session = _get_session_for_user(session_id, user_id)

        # Check session is stopped

        if session["status"] != "stopped":

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be stopped to remove strategies",
            )

        labels = _get_strategy_removal_labels(session_id, strategy_config_id)

        strategy_label = labels["strategy_label"]

        version_suffix = labels["version_suffix"]

        session_label = session.get("session_name") or f"id={session_id}"

        logger.info(
            f"Removing strategy {strategy_label}{version_suffix} from session {session_label}"
        )

        # Remove strategy from session

        success = db_manager.remove_strategy_from_session(
            session_id, strategy_config_id
        )

        if not success:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove strategy from session",
            )

        logger.info(
            f"Strategy {strategy_label}{version_suffix} removed from session {session_label}"
        )

        return {
            "message": "Strategy removed successfully",
            "session_id": session_id,
            "strategy_config_id": strategy_config_id,
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error removing strategy from session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing strategy",
        )


@router.get("/sessions/{session_id}/strategies")
async def get_session_strategies(session_id: int, authorization: str = AUTH_HEADER):
    """

    Get all strategies configured for a session.

    Returns list of strategy configurations including symbols, timeframes, and risk parameters.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this session",
            )

        # Get strategies

        strategies = db_manager.get_session_strategies(session_id)

        return {"strategies": strategies}

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting session strategies {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving strategies",
        )


# =============================================================================

# Manual Trading Endpoints

# =============================================================================


@router.put("/sessions/{session_id}/positions/{position_id}")
async def modify_position(
    session_id: int,
    position_id: int,
    request: PositionModifyRequest,
    authorization: str = AUTH_HEADER,
):
    """

    Modify an open position's stop loss or take profit.

    At least one of stop_loss or take_profit must be provided.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Modifying position {position_id} in session {session_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this position",
            )

        # Validate at least one parameter provided

        if request.stop_loss is None and request.take_profit is None:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of stop_loss or take_profit must be provided",
            )

        # If session is running, modify through LiveTradingSession

        if session_id in active_sessions:

            trading_session = active_sessions[session_id]

            if not trading_session.engine or not trading_session.engine.trade:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Trade engine not initialized",
                )

            trade = trading_session.engine.trade

            success = trade.PositionModify(
                ticket=position_id,
                sl=request.stop_loss or 0.0,
                tp=request.take_profit or 0.0,
            )

            if not success:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to modify position",
                )

            logger.info(f"Position {position_id} modified successfully")

            return {
                "message": "Position modified successfully",
                "position_id": position_id,
                "stop_loss": request.stop_loss,
                "take_profit": request.take_profit,
            }

        else:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be running to modify positions",
            )

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error modifying position {position_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while modifying position: {str(e)}",
        )


@router.post("/sessions/{session_id}/orders")
async def create_manual_order(
    session_id: int, request: ManualOrderRequest, authorization: str = AUTH_HEADER
):
    """Execute a manual order with optional pips-based SL/TP."""
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Manual order request for session {session_id}: {request}")

        _, trading_session = _get_active_session(
            session_id, user_id, action="place orders"
        )

        info, symbol_info = _get_symbol_info(request.symbol)

        entry_price, direction_sl, direction_tp = _get_entry_price_and_direction(
            request.type, info
        )

        stop_loss, take_profit = _calculate_sl_tp(
            entry_price,
            request.sl_pips,
            request.tp_pips,
            symbol_info,
            direction_sl,
            direction_tp,
        )

        engine = trading_session.engine

        trade = engine.trade if engine else None

        if not trade:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Trade engine not initialized",
            )

        if engine:

            trade.SetTypeFilling(engine._get_supported_filling_mode(request.symbol))

        comment = request.comment or "Manual Execution"

        order_type = request.type.lower()

        if order_type == "buy":

            success = trade.Buy(
                volume=request.volume,
                symbol=request.symbol,
                price=entry_price,
                sl=stop_loss or 0.0,
                tp=take_profit or 0.0,
                comment=comment,
            )

        elif order_type == "sell":

            success = trade.Sell(
                volume=request.volume,
                symbol=request.symbol,
                price=entry_price,
                sl=stop_loss or 0.0,
                tp=take_profit or 0.0,
                comment=comment,
            )

        else:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown order type: {request.type}",
            )

        if not success:

            retcode_desc = trade.ResultRetcodeDescription()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to execute order: {retcode_desc}",
            )

        return {
            "message": "Order executed successfully",
            "order_id": trade.ResultOrder(),
            "deal_id": trade.ResultDeal(),
            "price": trade.ResultPrice(),
            "volume": trade.ResultVolume(),
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error placing manual order: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error placing manual order: {str(e)}",
        )


@router.get("/sessions/{session_id}/orders")
async def get_session_orders(session_id: int, authorization: str = AUTH_HEADER):
    """Get pending orders for a session."""
    try:

        user_id = get_user_id_from_token(authorization)

        _, trading_session = _get_active_session(
            session_id, user_id, action="view orders"
        )

        client = trading_session.engine.client if trading_session.engine else None

        if not client:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MT5 client not initialized",
            )

        orders = client.orders_get() or []
        allowed_magics = set(_get_session_magic_numbers(session_id))
        normalized = []

        for order in orders:
            magic_value = getattr(order, "magic", None)
            try:
                magic_int = int(magic_value) if magic_value is not None else 0
            except (TypeError, ValueError):
                magic_int = 0

            if magic_int in allowed_magics:
                normalized.append(_map_mt5_order(order))

        return normalized

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error getting orders for session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving orders",
        )


@router.delete("/sessions/{session_id}/orders/{ticket}")
async def cancel_order(session_id: int, ticket: int, authorization: str = AUTH_HEADER):
    """Cancel a pending order by ticket."""
    try:

        user_id = get_user_id_from_token(authorization)

        _, trading_session = _get_active_session(
            session_id, user_id, action="cancel orders"
        )

        trade = trading_session.engine.trade if trading_session.engine else None

        if not trade:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Trade engine not initialized",
            )

        success = trade.OrderDelete(ticket)

        if not success:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel order",
            )

        return {"message": "Order cancelled successfully", "ticket": ticket}

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error cancelling order {ticket}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while cancelling order",
        )


@router.post("/sessions/{session_id}/orders/pending")
async def create_pending_order(
    session_id: int, request: PendingOrderRequest, authorization: str = AUTH_HEADER
):
    """Place a pending order with optional pips-based SL/TP."""
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Pending order request for session {session_id}: {request}")

        _, trading_session = _get_active_session(
            session_id, user_id, action="place pending orders"
        )

        info, symbol_info = _get_symbol_info(request.symbol)

        entry_price, direction_sl, direction_tp = _get_entry_price_and_direction(
            "buy" if "buy" in request.type else "sell", info
        )

        stop_loss, take_profit = _calculate_sl_tp(
            request.price,
            request.sl_pips,
            request.tp_pips,
            symbol_info,
            direction_sl,
            direction_tp,
        )

        trade = trading_session.engine.trade if trading_session.engine else None

        if not trade:

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Trade engine not initialized",
            )

        try:
            trade.SetTypeFillingBySymbol(request.symbol)
        except Exception as exc:
            logger.warning(f"Failed to set filling mode for {request.symbol}: {exc}")

        order_type = request.type.lower()

        order_type_map = {
            "buy_limit": getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2),
            "sell_limit": getattr(mt5, "ORDER_TYPE_SELL_LIMIT", 3),
            "buy_stop": getattr(mt5, "ORDER_TYPE_BUY_STOP", 4),
            "sell_stop": getattr(mt5, "ORDER_TYPE_SELL_STOP", 5),
        }

        mapped_type = order_type_map.get(order_type)
        if mapped_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown pending order type: {request.type}",
            )

        success = trade.OrderOpen(
            symbol=request.symbol,
            order_type=int(mapped_type),
            volume=request.volume,
            price=request.price,
            sl=stop_loss or 0.0,
            tp=take_profit or 0.0,
            comment=request.comment or "Manual Pending Order",
        )

        if not success:
            logger.error(
                f"Pending order failed | retcode={trade.ResultRetcodeDescription()} "
                f"comment={trade.ResultComment()}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to place pending order",
            )

        return {
            "message": "Pending order placed successfully",
            "order": {
                "symbol": request.symbol,
                "type": request.type,
                "price": request.price,
                "volume": request.volume,
            },
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error placing pending order: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error placing pending order: {str(e)}",
        )


@router.delete("/sessions/{session_id}/positions/{position_id}")
async def close_position(
    session_id: int, position_id: int, authorization: str = AUTH_HEADER
):
    """

    Manually close an open position.

    Closes the position at current market price.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Closing position {position_id} in session {session_id}")

        # Get session

        session = db_manager.get_live_session(session_id)

        if not session:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Verify ownership

        if session["user_id"] != user_id:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to close this position",
            )

        # If session is running, close through LiveTradingSession

        if session_id in active_sessions:

            trading_session = active_sessions[session_id]

            client = (
                trading_session.engine.client
                if trading_session.engine and trading_session.engine.client
                else trading_session.mt5_client
            )

            positions = client.positions_get(ticket=position_id) if client else []

            if not positions:

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Position {position_id} not found or already closed",
                )

            # Close position via ExecutionEngine

            position = positions[0]

            success = await trading_session.execution_engine.close_position(
                position=position, reason="manual"
            )

            if not success:

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to close position",
                )

            logger.info(f"Position {position_id} closed successfully")

            return {
                "message": "Position closed successfully",
                "position_id": position_id,
                "reason": "manual",
            }

        else:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session must be running to close positions",
            )

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error closing position {position_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while closing position: {str(e)}",
        )


@router.post("/sessions/{session_id}/positions/close-all")
async def close_all_positions(session_id: int, authorization: str = AUTH_HEADER):
    """

    Close all open positions for a session.

    Closes all positions at current market price.

    """
    try:

        user_id = get_user_id_from_token(authorization)

        logger.info(f"Closing all positions in session {session_id}")

        _, trading_session = _get_active_session(
            session_id, user_id, action="close positions"
        )

        client = (
            trading_session.engine.client
            if trading_session.engine and trading_session.engine.client
            else trading_session.mt5_client
        )

        positions = client.positions_get() if client else []

        allowed_magics = set(_get_session_magic_numbers(session_id))

        active_positions = {}

        for pos in positions:

            magic_value = getattr(pos, "magic", None)

            try:

                magic_int = int(magic_value) if magic_value is not None else 0

            except (TypeError, ValueError):

                magic_int = 0

            if magic_int in allowed_magics:

                active_positions[int(getattr(pos, "ticket", 0))] = pos

        if not active_positions:

            return {
                "message": "No open positions to close",
                "closed_count": 0,
                "failed_count": 0,
            }

        closed_count, failed_positions = await _close_positions(
            trading_session, active_positions
        )

        failed_count = len(failed_positions)

        logger.info(f"Closed {closed_count} positions, {failed_count} failed")

        response = {
            "message": f"Closed {closed_count} positions successfully",
            "closed_count": closed_count,
            "failed_count": failed_count,
        }

        if failed_positions:

            response["failed_positions"] = failed_positions

        return response

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error closing all positions for session {session_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while closing all positions: {str(e)}",
        )


# =============================================================================

# WebSocket Endpoint for Real-Time Updates

# =============================================================================


@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """

    Websocket endpoint for real-time live trading updates.

    Clients can connect to this endpoint to receive real-time updates for:

    - Signal detection, approval, and rejection

    - Position opening, updates, and closing

    - Session status changes

    - Log messages

    Clients can send subscription messages to control which channels they receive:

    {

        "action": "subscribe",

        "channels": ["signals", "positions", "status", "logs"]

    }

    """
    # Connect to the live trading manager

    await live_trading_manager.connect(session_id, websocket)

    logger.info(f"WebSocket connected for session {session_id}")

    try:

        while True:

            # Receive messages from client

            data = await websocket.receive_json()

            # Handle subscription updates

            if data.get("action") == "subscribe":

                channels = data.get("channels", [])

                await live_trading_manager.subscribe(session_id, websocket, channels)

                await websocket.send_json(
                    {"type": "subscription_updated", "channels": channels}
                )

                logger.info(
                    f"WebSocket subscription updated for session {session_id}: {channels}"
                )

    except WebSocketDisconnect:

        logger.info(f"WebSocket disconnected for session {session_id}")

        await live_trading_manager.disconnect(session_id, websocket)

    except Exception as e:

        logger.error(f"WebSocket error for session {session_id}: {e}")

        await live_trading_manager.disconnect(session_id, websocket)



