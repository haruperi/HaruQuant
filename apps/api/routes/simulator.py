"""Trading simulator and backtest API routes."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from apps.api.auth_utils import get_user_id_from_token
from apps.api.websocket import backtest_log_manager
from apps.utils.logger import logger
from apps.mt5 import get_mt5_api
from apps.mt5.client import MT5Client
from apps.trading import Engine
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.utils.data_getters import load_dukascopy
from apps.utils.data_manipulator import TicksGenerator
from apps.utils.data_validator import DataValidator

router = APIRouter()
backtest_router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)
mt5 = get_mt5_api()


def _object_to_dict(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    try:
        return dict(vars(value))
    except Exception:
        return {}


class _EngineSimulatorFacade:
    def __init__(self, engine: Engine):
        self._simulator = engine
        self.engine = engine

    @property
    def _positions_data(self) -> Dict[int, Any]:
        return {
            int(getattr(pos, "ticket", getattr(pos, "position_id", 0)) or 0): pos
            for pos in self.engine.state.trading_deals
        }

    @property
    def _orders_data(self) -> Dict[int, Any]:
        return {
            int(getattr(order, "ticket", 0) or 0): order
            for order in self.engine.state.trading_orders
        }

    @property
    def _account_data(self):
        return self.engine.account_info()

    def monitor_positions(self):
        return self.engine.monitor_positions(verbose=False)

    def monitor_account(self, _totals=None):
        return self.engine.monitor_account(verbose=False)

    def modify_position(self, pos_data: dict, new_sl=None, new_tp=None):
        ticket = int(pos_data.get("ticket") or pos_data.get("position_id") or pos_data.get("identifier") or 0)
        result = self.engine.order_send(
            {
                "action": 6,
                "position": ticket,
                "symbol": pos_data.get("symbol", ""),
                "sl": float(new_sl or 0.0),
                "tp": float(new_tp or 0.0),
            }
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009

    def close_position(self, pos_data: dict, reason: str = "manual"):
        symbol_name = str(pos_data.get("symbol", "") or "")
        pos_type = int(pos_data.get("type", 0) or 0)
        close_type = 1 if pos_type == 0 else 0
        tick = self.engine.symbol_info_tick(symbol_name)
        close_price = float(getattr(tick, "bid", 0.0) if close_type == 1 else getattr(tick, "ask", 0.0))
        result = self.engine.order_send(
            {
                "action": 1,
                "symbol": symbol_name,
                "type": close_type,
                "position": int(pos_data.get("ticket") or pos_data.get("position_id") or pos_data.get("identifier") or 0),
                "volume": float(pos_data.get("volume") or 0.0),
                "price": close_price,
                "comment": f"Session {reason}",
            }
        )
        return int(getattr(result, "retcode", 0) or 0) in (10008, 10009)

    def order_modify(self, order_data: dict, new_open_price: float, new_sl: float, new_tp: float):
        result = self.engine.order_send(
            {
                "action": 7,
                "order": int(order_data.get("ticket") or 0),
                "price": float(new_open_price or 0.0),
                "sl": float(new_sl or 0.0),
                "tp": float(new_tp or 0.0),
            }
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009

    def order_delete(self, order_data: dict):
        result = self.engine.order_send(
            {
                "action": 8,
                "order": int(order_data.get("ticket") or 0),
            }
        )
        return int(getattr(result, "retcode", 0) or 0) == 10009


class SimulatorSession:
    def __init__(self, session_id: int, config: Dict[str, Any], db: DatabaseManager):
        self.session_id = session_id
        self.config = dict(config)
        self.db = db
        self.engine = Engine(backend="sim")
        self.simulator = _EngineSimulatorFacade(self.engine)
        self.speed_multiplier = float(self.config.get("speed_multiplier", 1.0) or 1.0)
        self.current_bar_index = int(self.config.get("current_bar_index", 0) or 0)
        self.total_bars = 0
        self.symbol_digits = 5
        self.paused = False
        self.strategy = None
        self.replay_trades = []
        self.data = None
        self._seed_account()
        self._ensure_symbol()

    def _seed_account(self):
        initial_balance = float(self.config.get("initial_balance", 10000.0) or 10000.0)
        account = self.engine.account_info()
        account["balance"] = initial_balance
        account["credit"] = 0.0
        account["profit"] = 0.0
        account["equity"] = initial_balance
        account["margin"] = 0.0
        account["margin_free"] = initial_balance
        account["margin_level"] = 0.0

    def _ensure_symbol(self):
        symbol_name = str(self.config.get("symbol", "") or "")
        for row in self.engine.state.trading_symbols:
            if str(getattr(row, "name", "") or "") == symbol_name:
                self.symbol_digits = int(getattr(row, "digits", 5) or 5)
                return row
        symbol_info = self.engine.client.symbol_info(symbol_name)
        if symbol_info is None:
            raise ValueError(f"Symbol info unavailable for {symbol_name}")
        self.engine.state.trading_symbols.append(symbol_info)
        self.symbol_digits = int(getattr(symbol_info, "digits", 5) or 5)
        return symbol_info

    def set_strategy(self, strategy_instance):
        self.strategy = strategy_instance
        if hasattr(self.strategy, "on_init"):
            self.strategy.on_init()

    def set_replay_trades(self, trades):
        self.replay_trades = list(trades or [])

    def load_historical_bars(self):
        symbol = str(self.config.get("symbol", "") or "")
        timeframe = str(self.config.get("timeframe", "M1") or "M1")
        number_of_bars = self.config.get("number_of_bars")
        start_time = self.config.get("start_time")
        end_time = self.config.get("end_time")
        if number_of_bars:
            data = self.engine.client.get_bars(symbol=symbol, timeframe=timeframe, count=int(number_of_bars))
        else:
            date_from = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else None
            date_to = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
            data = self.engine.client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
        if data is None or data.empty:
            raise ValueError("No historical bars loaded for simulator session")
        if self.strategy is not None and hasattr(self.strategy, "on_bar"):
            data = self.strategy.on_bar(data)
        self.data = data
        self.total_bars = len(data)

    def _bar_row(self, index: int):
        if self.data is None or index < 0 or index >= len(self.data):
            return None
        return self.data.iloc[index]

    def get_bar(self, index: int):
        row = self._bar_row(index)
        if row is None:
            return None
        payload = row.to_dict()
        payload["time"] = self.data.index[index].isoformat() if hasattr(self.data.index[index], "isoformat") else str(self.data.index[index])
        return payload

    def _update_symbol_from_bar(self, row, index: int):
        symbol = str(self.config.get("symbol", "") or "")
        symbol_info = self.engine.symbol_info(symbol)
        close_price = float(row.get("close", row.get("Close", 0.0)) or 0.0)
        spread_points = float(row.get("spread", row.get("Spread", 0.0)) or 0.0)
        point = float(getattr(symbol_info, "point", 0.00001) or 0.00001)
        bid = close_price
        ask = close_price + (spread_points * point)
        self.engine.state.current_tick_datetime = self.data.index[index].to_pydatetime() if hasattr(self.data.index[index], 'to_pydatetime') else self.data.index[index]
        self.engine.state.current_tick_epoch = int(self.data.index[index].timestamp()) if hasattr(self.data.index[index], 'timestamp') else None
        self.engine._build_symbol_map()
        self.engine._update_symbol_tick(self.engine._build_symbol_map(), symbol, bid, ask)
        return symbol, bid, ask

    def _account_snapshot(self):
        account = self.engine.account_info()
        return {
            "balance": float(account.get("balance", 0.0) or 0.0),
            "equity": float(account.get("equity", 0.0) or 0.0),
            "margin": float(account.get("margin", 0.0) or 0.0),
            "profit": float(account.get("profit", 0.0) or 0.0),
            "margin_free": float(account.get("margin_free", 0.0) or 0.0),
        }

    def process_bar_at_index(self, index: int):
        row = self._bar_row(index)
        if row is None:
            return self._account_snapshot()
        symbol, bid, ask = self._update_symbol_from_bar(row, index)
        self.engine._apply_tick_signals(
            symbol_name=symbol,
            bid=bid,
            ask=ask,
            entry_signal=float(row.get("entry_signal", 0.0) or 0.0),
            exit_signal=float(row.get("exit_signal", row.get("exit_trade", 0.0)) or 0.0),
            pending_signal=float(row.get("pending_signal", 0.0) or 0.0),
            cancel_pending_signal=float(row.get("cancel_pending_signal", 0.0) or 0.0),
            pending_signal_2=float(row.get("pending_signal_2", 0.0) or 0.0),
            cancel_pending_signal_2=float(row.get("cancel_pending_signal_2", 0.0) or 0.0),
            signal_price=float(row.get("price", 0.0) or 0.0),
            signal_price_2=float(row.get("price_2", 0.0) or 0.0),
            sl=float(row.get("sl", 0.0) or 0.0),
            tp=float(row.get("tp", 0.0) or 0.0),
            volume=float(self.config.get("lot_size", 0.1) or 0.1),
            verbose=False,
        )
        self.engine.monitor_pending_orders(verbose=False)
        self.engine.monitor_positions(verbose=False)
        self.engine.monitor_account(verbose=False)
        return self._account_snapshot()

    def get_indicators_at_index(self, index: int):
        row = self._bar_row(index)
        if row is None:
            return {}
        excluded = {"open", "high", "low", "close", "tick_volume", "real_volume", "spread", "Open", "High", "Low", "Close", "TickVolume", "RealVolume", "Spread"}
        out = {}
        for key, value in row.to_dict().items():
            if str(key) in excluded:
                continue
            if isinstance(value, (int, float, str, bool)) or value is None:
                out[str(key)] = value
        return out

    def execute_trade(self, request: Dict[str, Any]):
        row = self._bar_row(max(self.current_bar_index - 1, 0)) or self._bar_row(0)
        if row is not None:
            symbol, bid, ask = self._update_symbol_from_bar(row, max(self.current_bar_index - 1, 0))
        else:
            symbol = str(self.config.get("symbol", "") or "")
            tick = self.engine.symbol_info_tick(symbol)
            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
        side = str(request.get("side", "buy") or "buy").lower()
        order_type = 0 if side == "buy" else 1
        price = request.get("price")
        if price is None:
            price = ask if order_type == 0 else bid
        result = self.engine.order_send(
            {
                "action": 1,
                "symbol": symbol,
                "type": order_type,
                "volume": float(request.get("volume", 0.1) or 0.1),
                "price": float(price or 0.0),
                "sl": float(request.get("sl") or 0.0),
                "tp": float(request.get("tp") or 0.0),
                "comment": str(request.get("comment") or "Manual trade"),
            }
        )
        self.engine.monitor_positions(verbose=False)
        self.engine.monitor_account(verbose=False)
        return _object_to_dict(result)

    def place_pending_order(self, request: Dict[str, Any]):
        order_type_map = {
            "buy_limit": 2,
            "sell_limit": 3,
            "buy_stop": 4,
            "sell_stop": 5,
        }
        symbol = str(self.config.get("symbol", "") or "")
        result = self.engine.order_send(
            {
                "action": 5,
                "symbol": symbol,
                "type": int(order_type_map.get(str(request.get("type", "")).lower(), 0)),
                "volume": float(request.get("volume", 0.1) or 0.1),
                "price": float(request.get("price", 0.0) or 0.0),
                "sl": float(request.get("sl") or 0.0),
                "tp": float(request.get("tp") or 0.0),
                "comment": str(request.get("comment") or "Pending order"),
            }
        )
        self.engine.monitor_account(verbose=False)
        return _object_to_dict(result)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def save_state(self):
        self.db.update_simulation_session(self.session_id, current_bar_index=self.current_bar_index)

    def seek_to_bar(self, index: int):
        self.current_bar_index = max(0, min(int(index), max(self.total_bars - 1, 0)))
        self.save_state()

    def stop(self):
        try:
            self.engine.client.shutdown()
        except Exception:
            pass


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


def _position_info_to_dict(position: Any) -> dict:
    if isinstance(position, dict):
        return position
    if hasattr(position, "_asdict"):
        return dict(position._asdict())
    time_value = position.Time() if hasattr(position, "Time") else None
    return {
        "ticket": int(getattr(position, "ticket", 0) or 0),
        "identifier": int(getattr(position, "identifier", 0) or 0),
        "symbol": getattr(position, "symbol", ""),
        "type": int(getattr(position, "type", 0) or 0),
        "volume": float(getattr(position, "volume", 0.0) or 0.0),
        "price_open": float(getattr(position, "price_open", 0.0) or 0.0),
        "price_current": float(getattr(position, "price_current", 0.0) or 0.0),
        "sl": float(getattr(position, "sl", 0.0) or 0.0),
        "tp": float(getattr(position, "tp", 0.0) or 0.0),
        "profit": float(getattr(position, "profit", 0.0) or 0.0),
        "swap": float(getattr(position, "swap", 0.0) or 0.0),
        "commission": float(getattr(position, "commission", 0.0) or 0.0),
        "time": int(time_value) if time_value is not None else None,
        "comment": getattr(position, "comment", ""),
    }


def _order_info_to_dict(order: Any) -> dict:
    if isinstance(order, dict):
        return order
    if hasattr(order, "_asdict"):
        return dict(order._asdict())
    time_value = order.TimeSetup() if hasattr(order, "TimeSetup") else None
    return {
        "ticket": int(getattr(order, "ticket", 0) or 0),
        "identifier": int(getattr(order, "position_id", 0) or 0),
        "symbol": getattr(order, "symbol", ""),
        "type": int(getattr(order, "type", 0) or 0),
        "volume_initial": float(getattr(order, "volume_initial", 0.0) or 0.0),
        "volume_current": float(getattr(order, "volume_current", 0.0) or 0.0),
        "price_open": float(getattr(order, "price_open", 0.0) or 0.0),
        "sl": float(getattr(order, "sl", 0.0) or 0.0),
        "tp": float(getattr(order, "tp", 0.0) or 0.0),
        "time": int(time_value) if time_value is not None else None,
        "comment": getattr(order, "comment", ""),
    }


def _collect_positions_orders(active: SimulatorSession) -> tuple[list[dict], list[dict]]:
    positions_raw = active.simulator._simulator.positions_get() or []
    orders_raw = active.simulator._simulator.orders_get() or []
    positions = [_normalize_position(_position_info_to_dict(pos)) for pos in positions_raw]
    orders = [_normalize_order(_order_info_to_dict(order)) for order in orders_raw]
    return positions, orders


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

    positions, orders = _collect_positions_orders(active)

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

    positions, orders = _collect_positions_orders(active)

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

    positions, orders = _collect_positions_orders(active)

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

    positions, orders = _collect_positions_orders(active)

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

        positions, orders = _collect_positions_orders(active)

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

        positions, orders = _collect_positions_orders(active)

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

        positions, orders = _collect_positions_orders(active)

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

        positions, orders = _collect_positions_orders(active)

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


# ========================================
# Backtest Routes
# ========================================

class BacktestRequest(BaseModel):
    """Request payload for running a backtest."""

    symbol: str
    timeframe: str
    range_by: Optional[str] = "dates"  # "dates" or "bars"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    warmup_by: Optional[str] = "date"  # "date" or "bars"
    warmup_start_date: Optional[str] = None
    warmup_bars: Optional[int] = None
    initial_capital: float = 10000
    commission: float = 0.0
    slippage_type: Optional[str] = "fixed"
    slippage: int = 0
    slippage_min: int = 0
    slippage_max: int = 10
    spread_type: Optional[str] = "use-broker"
    spread: int = 20
    spread_min: int = 10
    spread_max: int = 50
    leverage: int = 100
    data_source: Optional[str] = "mt5"
    engine_type: Optional[str] = "simulator"
    data_resolution: Optional[str] = "trading_timeframe"
    position_sizing_method: Optional[str] = "fixed_lot"
    lot_size: float = 0.1
    risk_percent: float = 1.0
    base_lot_size: float = 0.1
    milestone_amount: float = 3000
    lot_increment: float = 0.2
    kelly_fraction_limit: float = 0.25
    fraction: float = 2.0
    alias: Optional[str] = None
    description: Optional[str] = None


class BacktestResponse(BaseModel):
    """Response model for backtest runs."""

    backtest_id: int
    strategy_id: Optional[int] = None
    strategy_version_id: Optional[int]
    status: str
    strategy_name: str
    symbol: Optional[str]
    timeframe: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    initial_balance: Optional[float]
    final_balance: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    created_at: str
    completed_at: Optional[str]
    alias: Optional[str] = None
    description: Optional[str] = None
    engine_type: Optional[str] = None
    data_resolution: Optional[str] = None
    trades: Optional[List[Dict[str, Any]]] = None


class BacktestUpdateRequest(BaseModel):
    """Request payload for updating backtest metadata."""

    alias: Optional[str] = None
    description: Optional[str] = None


class PortfolioBacktestRequest(BaseModel):
    """Request payload for running a multi-symbol portfolio backtest."""

    symbols: str  # Comma-separated list of symbols
    timeframe: str
    range_by: Optional[str] = "dates"  # "dates" or "bars"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
    warmup_by: Optional[str] = "date"  # "date" or "bars"
    warmup_start_date: Optional[str] = None
    warmup_bars: Optional[int] = None
    initial_capital: float = 50000  # Higher default for portfolio
    commission: float = 0.0
    slippage_type: Optional[str] = "fixed"
    slippage: int = 0
    slippage_min: int = 0
    slippage_max: int = 10
    spread_type: Optional[str] = "use-broker"
    spread: int = 20
    spread_min: int = 10
    spread_max: int = 50
    leverage: int = 100
    data_source: Optional[str] = "mt5"
    data_resolution: Optional[str] = "trading_timeframe"
    allocation_method: Optional[str] = "equal_weight"  # "equal_weight" or "risk_parity"
    lot_size: float = 0.1  # Base lot size per symbol
    position_sizing_method: Optional[str] = "fixed_lot"
    risk_percent: float = 1.0
    base_lot_size: float = 0.1
    milestone_amount: float = 3000
    lot_increment: float = 0.2
    kelly_fraction_limit: float = 0.25
    fraction: float = 2.0
    alias: Optional[str] = None
    description: Optional[str] = None


class PortfolioBacktestResponse(BaseModel):
    """Response model for portfolio backtest runs."""

    backtest_id: int
    status: str
    portfolio_name: str
    symbols: List[str]
    timeframe: str
    start_date: Optional[str]
    end_date: Optional[str]
    initial_balance: float
    final_balance: Optional[float]
    total_return: Optional[float]
    total_return_pct: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    created_at: str
    completed_at: Optional[str]
    allocation_method: str
    asset_results: Optional[Dict[str, Dict[str, Any]]] = None


def _parse_request_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


def _parse_symbol(value: str) -> str:
    """Parse single symbol from string (for backward compatibility)."""
    symbols = [s.strip().upper() for s in value.split(",") if s.strip()]
    if not symbols:
        raise ValueError("Symbol is required")
    if len(symbols) > 1:
        raise ValueError(
            f"Multi-symbol backtest detected ({', '.join(symbols)}). "
            "Please use the POST /api/backtest/portfolio/run/{{strategy_id}} endpoint for multi-symbol backtests."
        )
    return symbols[0]


def _parse_symbols(value: str) -> List[str]:
    """Parse multiple symbols from comma-separated string."""
    symbols = [s.strip().upper() for s in value.split(",") if s.strip()]
    if not symbols:
        raise ValueError("At least one symbol is required")
    return symbols


def _resolve_modelling(mode: Optional[str]) -> str:
    resolved = str(mode or "trading_timeframe").strip().lower()
    allowed = {
        "trading_timeframe",
        "m1_ohlc",
        "synthetic_ticks",
        "real_ticks",
    }
    if resolved not in allowed:
        raise ValueError(f"Unsupported data_resolution: {mode}")
    return resolved


# ----------------------------
# Vectorized Engine Support
# ----------------------------
def _resolve_engine_type(value: Optional[str]) -> str:
    raw = str(value or "event_driven").strip().lower()
    if raw == "simulator":
        raw = "event_driven"
    raw = raw.replace("-", "_")
    if raw == "vectorized":
        raw = "vectorised"
    if raw not in {"event_driven", "vectorised"}:
        raise ValueError(f"Unsupported engine_type: {value}")
    return raw


def _load_mt5_bars(
    client: MT5Client,
    symbol: str,
    timeframe: str,
    request: BacktestRequest,
):
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        # Add warmup bars to the total count
        total_bars = request.number_of_bars
        if request.warmup_by == "bars" and request.warmup_bars:
            total_bars += request.warmup_bars
        return client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=total_bars,
        )

    # For date-based range, use warmup_start_date if provided
    start_date = _parse_request_date(request.start_date)
    if request.warmup_by == "date" and request.warmup_start_date:
        start_date = _parse_request_date(request.warmup_start_date)

    return client.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        date_from=start_date,
        date_to=_parse_request_date(request.end_date),
    )


def _load_mt5_ticks(client: MT5Client, symbol: str, request: BacktestRequest):
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        tick_count = request.number_of_bars * 100
        # Add warmup bars to tick count estimate
        if request.warmup_by == "bars" and request.warmup_bars:
            tick_count += request.warmup_bars * 100
        return client.get_ticks(symbol=symbol, count=tick_count)

    # For date-based range, use warmup_start_date if provided
    start_date = _parse_request_date(request.start_date)
    if request.warmup_by == "date" and request.warmup_start_date:
        start_date = _parse_request_date(request.warmup_start_date)

    return client.get_ticks(
        symbol=symbol,
        start=start_date,
        end=_parse_request_date(request.end_date),
    )


def _load_data(  # noqa: C901
    request: BacktestRequest,
    symbol: str,
    data_mode: str,
    user_id: int,
) -> Tuple[Any, Optional[Any], str]:
    data_source = (request.data_source or "mt5").strip().lower()

    if data_source not in {"mt5", "metatrader5", "dukascopy"}:
        raise ValueError(f"Unsupported data_source: {request.data_source}")

    data = None
    step_data = None

    if data_source in {"mt5", "metatrader5"}:
        credentials = db_manager.get_mt5_credentials(user_id)
        client = MT5Client()
        if credentials:
            ok = client.connect(
                path=credentials.get("path", ""),
                login=credentials.get("login", 0),
                password=credentials.get("password", ""),
                server=credentials.get("server", ""),
            )
        else:
            ok = False
        if not ok:
            raise RuntimeError("Failed to connect to MT5")

        try:
            data = _load_mt5_bars(client, symbol, request.timeframe, request)
            if data is None or data.empty:
                raise ValueError("No trading timeframe data loaded from MT5")
            data = DataValidator.prepare_data(data)

            if data_mode in {"m1_ohlc", "synthetic_ticks"}:
                step_data = _load_mt5_bars(client, symbol, "M1", request)
                if step_data is None or step_data.empty:
                    raise ValueError("No M1 data loaded from MT5")
                step_data = DataValidator.prepare_data(step_data)
            elif data_mode == "real_ticks":
                step_data = _load_mt5_ticks(client, symbol, request)
                if step_data is None or len(step_data) == 0:
                    raise ValueError("No tick data loaded from MT5")
                step_data.columns = [str(c).lower() for c in step_data.columns]
        finally:
            client.shutdown()
    else:
        if request.range_by == "bars":
            if request.number_of_bars is None:
                raise ValueError("number_of_bars is required when range_by='bars'")
            # Add warmup bars to total count
            total_bars = request.number_of_bars
            if request.warmup_by == "bars" and request.warmup_bars:
                total_bars += request.warmup_bars
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                count=total_bars,
            )
        else:
            # Use warmup_start_date if provided for date range
            start_date = request.start_date
            if request.warmup_by == "date" and request.warmup_start_date:
                start_date = request.warmup_start_date
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                start_date=start_date,
                end_date=request.end_date,
            )

        if data is None or data.empty:
            raise ValueError("No trading timeframe data loaded from Dukascopy")
        data = DataValidator.prepare_data(data)

        if data_mode == "real_ticks":
            raise ValueError("Real ticks are not available for Dukascopy source")
        if data_mode in {"m1_ohlc", "synthetic_ticks"}:
            # Use warmup_start_date for M1 data as well
            start_date = request.start_date
            if request.warmup_by == "date" and request.warmup_start_date:
                start_date = request.warmup_start_date
            step_data = load_dukascopy(
                symbol=symbol,
                timeframe="M1",
                start_date=start_date,
                end_date=request.end_date,
            )
            if step_data is None or step_data.empty:
                raise ValueError("No M1 data loaded from Dukascopy")
            step_data = DataValidator.prepare_data(step_data)

    return data, step_data, data_source


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

    return version, strategy, strategy_class


def _seed_engine_account(engine: Engine, initial_capital: float) -> None:
    account = engine.account_info()
    account["balance"] = float(initial_capital)
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = float(initial_capital)
    account["margin"] = 0.0
    account["margin_free"] = float(initial_capital)
    account["margin_level"] = 0.0


def _ensure_engine_symbol(engine: Engine, symbol_name: str):
    for row in engine.state.trading_symbols:
        if str(getattr(row, "name", "") or "") == str(symbol_name):
            return row
    symbol_row = engine.client.symbol_info(symbol_name)
    if symbol_row is None:
        raise ValueError(f"Symbol info unavailable for {symbol_name}")
    engine.state.trading_symbols.append(symbol_row)
    return symbol_row


def _resolve_tick_generator_config(request: BacktestRequest, data_mode: str) -> tuple[str, str]:
    model_map = {
        "trading_timeframe": "timeframe_ticks",
        "m1_ohlc": "m1_ticks",
        "synthetic_ticks": "synthetic_ticks",
        "real_ticks": "real_ticks",
    }
    spread_map = {
        "use-broker": "native_spread",
        "broker": "native_spread",
        "fixed": "fixed_spread",
        "fixed_spread": "fixed_spread",
        "variable": "variable_spread",
        "variable_spread": "variable_spread",
    }
    tick_model = model_map.get(str(data_mode), "timeframe_ticks")
    spread_model = spread_map.get(str(request.spread_type or "use-broker").strip().lower(), "native_spread")
    return tick_model, spread_model


def _generate_ticks_for_backtest(
    engine: Engine,
    symbol_name: str,
    timeframe: str,
    request: BacktestRequest,
    data_mode: str,
    bars_data,
    step_data=None,
):
    symbol_info = _ensure_engine_symbol(engine, symbol_name)
    tick_model, spread_model = _resolve_tick_generator_config(request, data_mode)
    point_value = float(getattr(symbol_info, "point", 0.00001) or 0.00001)

    generator_kwargs = {
        "model": tick_model,
        "trading_timeframe": timeframe,
        "point_value": point_value,
        "spread_model": spread_model,
    }
    if spread_model == "fixed_spread":
        generator_kwargs["fixed_spread_points"] = float(request.spread or 0)
    elif spread_model == "variable_spread":
        generator_kwargs["min_spread_points"] = float(request.spread_min or 0)
        generator_kwargs["max_spread_points"] = float(request.spread_max or request.spread_min or 0)

    if tick_model == "m1_ticks":
        generator_kwargs["m1_data"] = step_data
    elif tick_model == "synthetic_ticks":
        generator_kwargs["m1_data"] = step_data
    elif tick_model == "real_ticks":
        generator_kwargs["real_ticks"] = step_data

    ticks_generator = TicksGenerator(**generator_kwargs)
    ticks_data = ticks_generator.generate(bars_data.copy())
    if ticks_data is None or ticks_data.empty:
        raise ValueError(f"No ticks generated for {symbol_name}")
    return ticks_data, tick_model



async def _run_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: BacktestRequest,
) -> None:
    """Background task to run a backtest using the simulator."""
    loop = asyncio.get_event_loop()

    def log_sink(record: Any) -> None:
        log_data = {
            "timestamp": record.time.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "source": record.name,
            "backtest_id": backtest_id,
        }
        with suppress(Exception):
            asyncio.run_coroutine_threadsafe(
                backtest_log_manager.broadcast(backtest_id, log_data), loop
            )

    handler_id = logger.add(log_sink, level="INFO", raw=True)

    try:
        await asyncio.sleep(2.0)
        db_manager.update_backtest_status(backtest_id, "running")

        symbol = _parse_symbol(request.symbol)
        engine_type = _resolve_engine_type(request.engine_type)
        data_mode = _resolve_modelling(request.data_resolution)
        if engine_type == "vectorised" and data_mode != "trading_timeframe":
            raise ValueError(
                "Vectorized engine only supports trading_timeframe data resolution"
            )

        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )

        data, step_data, data_source = _load_data(
            request=request,
            symbol=symbol,
            data_mode=data_mode,
            user_id=user_id,
        )

        params = dict(version.get("parameters") or {})
        params["symbol"] = symbol
        params["timeframe"] = request.timeframe
        strategy_instance = strategy_class(params=params)
        if hasattr(strategy_instance, "on_init"):
            strategy_instance.on_init()
        if hasattr(strategy_instance, "on_bar"):
            data = strategy_instance.on_bar(data)

        engine = Engine(backend="sim")
        _seed_engine_account(engine, float(request.initial_capital))
        _ensure_engine_symbol(engine, symbol)

        ticks_data, tick_model = _generate_ticks_for_backtest(
            engine=engine,
            symbol_name=symbol,
            timeframe=request.timeframe,
            request=request,
            data_mode=data_mode,
            bars_data=data,
            step_data=step_data,
        )

        logger.info(
            f"Running simulator backtest {backtest_id} | "
            f"symbol={symbol} timeframe={request.timeframe} "
            f"engine={engine_type} mode={data_mode} ticks_model={tick_model} source={data_source}"
        )

        engine.configure_run_schedule(
            positions_every=1,
            pending_orders_every=1,
            account_every=4,
            portfolio_every=4,
            risk_every=4,
        )
        processed = engine.run(
            ticks_data,
            position_size=float(request.lot_size),
            monitor_verbose=False,
            show_progress=False,
        )

        completed_trades = engine.get_completed_trades()
        equity_curve = engine.get_equity_curve()
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)
        if equity_curve:
            db_manager.save_backtest_equity_curve(backtest_id, equity_curve)

        final_balance = float(engine.account_info().get("balance", request.initial_capital) or request.initial_capital)
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=final_balance,
        )
        logger.info(
            f"Backtest {backtest_id} completed successfully | processed_ticks={processed} trades={len(completed_trades)}"
        )
        engine.client.shutdown()

    except Exception as exc:
        logger.error(f"Backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
            logger.info(f"WebSocket handler removed for backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error removing WebSocket handler: {exc}")

        try:
            await asyncio.sleep(5.0)
            await backtest_log_manager.clear_buffer(backtest_id)
            logger.info(f"Log buffer cleared for backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error clearing log buffer: {exc}")

        logger.info(f"Background task completed for backtest {backtest_id}")


@backtest_router.post("/run/{strategy_id}", response_model=BacktestResponse)
async def run_backtest(
    strategy_id: int,
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    authorization: Annotated[Optional[str], Header()] = None,
) -> BacktestResponse:
    """Run a backtest for a strategy."""
    try:
        user_id = get_user_id_from_token(authorization)
        symbol = _parse_symbol(request.symbol)
        engine_type = _resolve_engine_type(request.engine_type)

        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy or active version not found",
            )

        version_id = int(strategy["active_version_id"])
        start_dt = _parse_request_date(request.start_date) or datetime.utcnow()
        end_dt = _parse_request_date(request.end_date) or datetime.utcnow()

        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",
            start_date=start_dt,
            end_date=end_dt,
            engine_type=engine_type,
            data_resolution=request.data_resolution or "trading_timeframe",
            config_hash=str(hash((strategy_id, symbol, request.timeframe))),
            symbols=[symbol],
            timeframes=[request.timeframe],
            initial_balance=request.initial_capital,
            alias=request.alias,
            description=request.description,
            strategy_version_id=version_id,
            user_id=user_id,
        )

        background_tasks.add_task(
            _run_backtest_task,
            backtest_id=backtest_id,
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
            request=request,
        )

        backtest_run = db_manager.get_backtest_run(backtest_id)
        if backtest_run is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "strategy_version_id": backtest_run.get("strategy_version_id"),
            "status": backtest_run["status"],
            "strategy_name": backtest_run["strategy_name"],
            "symbol": symbol,
            "timeframe": request.timeframe,
            "start_date": backtest_run["start_date"],
            "end_date": backtest_run["end_date"],
            "initial_balance": backtest_run["initial_balance"],
            "final_balance": backtest_run.get("final_balance"),
            "total_trades": backtest_run.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": backtest_run["created_at"],
            "completed_at": backtest_run.get("completed_at"),
            "engine_type": engine_type,
            "data_resolution": request.data_resolution or "trading_timeframe",
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Invalid backtest request: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Error starting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start backtest: {str(exc)}",
        )


@backtest_router.get("/strategy/{strategy_id}", response_model=List[BacktestResponse])
async def list_strategy_backtests(strategy_id: int) -> List[BacktestResponse]:
    """List all backtests for a strategy."""
    try:
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            return []

        backtests = db_manager.get_all_backtests(
            strategy_version_id=strategy["active_version_id"]
        )

        response_list = []
        for bt in backtests:
            response_list.append(
                BacktestResponse(
                    backtest_id=bt["backtest_id"],
                    strategy_id=strategy_id,
                    strategy_version_id=bt.get("strategy_version_id"),
                    status=bt["status"],
                    strategy_name=bt["strategy_name"],
                    symbol=",".join(bt.get("symbols", []) or []) or None,
                    timeframe=(
                        bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                    ),
                    start_date=bt.get("start_date"),
                    end_date=bt.get("end_date"),
                    initial_balance=bt.get("initial_balance"),
                    final_balance=bt.get("final_balance"),
                    total_trades=bt.get("total_trades"),
                    win_rate=None,
                    profit_factor=None,
                    sharpe_ratio=None,
                    max_drawdown=None,
                    created_at=bt["created_at"],
                    completed_at=bt.get("completed_at"),
                    alias=bt.get("alias"),
                    description=bt.get("description"),
                    engine_type=bt.get("engine_type"),
                    data_resolution=bt.get("data_resolution"),
                )
            )

        return response_list

    except Exception as exc:
        logger.error(f"Error listing backtests: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backtests: {str(exc)}",
        )


@backtest_router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(backtest_id: int) -> BacktestResponse:
    """Get a specific backtest."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        trades = []
        with suppress(Exception):
            trades = db_manager.get_backtest_trades(backtest_id)

        response_data = {
            "backtest_id": backtest["backtest_id"],
            "strategy_id": backtest.get("strategy_id"),
            "strategy_version_id": backtest.get("strategy_version_id"),
            "status": backtest["status"],
            "strategy_name": backtest["strategy_name"],
            "symbol": ",".join(backtest.get("symbols", []) or []) or None,
            "timeframe": (
                backtest.get("timeframes", [""])[0]
                if backtest.get("timeframes")
                else None
            ),
            "start_date": backtest.get("start_date"),
            "end_date": backtest.get("end_date"),
            "initial_balance": backtest.get("initial_balance"),
            "final_balance": backtest.get("final_balance"),
            "total_trades": backtest.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": backtest["created_at"],
            "completed_at": backtest.get("completed_at"),
            "alias": backtest.get("alias"),
            "description": backtest.get("description"),
            "engine_type": backtest.get("engine_type"),
            "data_resolution": backtest.get("data_resolution"),
            "trades": trades,
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backtest: {str(exc)}",
        )


@backtest_router.websocket("/ws/{backtest_id}/logs")
async def backtest_logs_websocket(websocket: WebSocket, backtest_id: int) -> None:
    """Websocket endpoint for streaming backtest logs in real time."""
    logger.info(f"WebSocket connection attempt for backtest {backtest_id}")
    await backtest_log_manager.connect(backtest_id, websocket)
    logger.info(f"WebSocket connected for backtest {backtest_id}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for backtest {backtest_id}")
        await backtest_log_manager.disconnect(backtest_id, websocket)
    except Exception as exc:
        logger.error(f"WebSocket error for backtest {backtest_id}: {exc}")
        await backtest_log_manager.disconnect(backtest_id, websocket)


@backtest_router.get("/", response_model=List[BacktestResponse])
async def list_all_backtests(
    user_id: int = 1, limit: int = 100
) -> List[BacktestResponse]:
    """List all backtests across all strategies."""
    try:
        backtests = db_manager.get_all_backtests(user_id=user_id, limit=limit)
        response_list = []
        for bt in backtests:
            response_list.append(
                BacktestResponse(
                    backtest_id=bt["backtest_id"],
                    strategy_id=bt.get("strategy_id"),
                    strategy_version_id=bt.get("strategy_version_id"),
                    status=bt["status"],
                    strategy_name=bt["strategy_name"],
                    symbol=",".join(bt.get("symbols", []) or []) or None,
                    timeframe=(
                        bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                    ),
                    start_date=bt.get("start_date"),
                    end_date=bt.get("end_date"),
                    initial_balance=bt.get("initial_balance"),
                    final_balance=bt.get("final_balance"),
                    total_trades=bt.get("total_trades"),
                    win_rate=None,
                    profit_factor=None,
                    sharpe_ratio=None,
                    max_drawdown=None,
                    created_at=bt["created_at"],
                    completed_at=bt.get("completed_at"),
                    alias=bt.get("alias"),
                    description=bt.get("description"),
                    engine_type=bt.get("engine_type"),
                    data_resolution=bt.get("data_resolution"),
                )
            )
        return response_list

    except Exception as exc:
        logger.error(f"Error listing all backtests: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list all backtests: {str(exc)}",
        )


@backtest_router.put("/{backtest_id}", response_model=BacktestResponse)
async def update_backtest(
    backtest_id: int, request: BacktestUpdateRequest
) -> BacktestResponse:
    """Update backtest metadata (alias, description)."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        if request.alias is not None or request.description is not None:
            db_manager.update_backtest_metadata(
                backtest_id=backtest_id,
                alias=request.alias,
                description=request.description,
            )

        updated = db_manager.get_backtest_run(backtest_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load backtest {backtest_id}",
            )

        response_data = {
            "backtest_id": updated["backtest_id"],
            "strategy_id": updated.get("strategy_id"),
            "strategy_version_id": updated.get("strategy_version_id"),
            "status": updated["status"],
            "strategy_name": updated["strategy_name"],
            "symbol": ",".join(updated.get("symbols", []) or []) or None,
            "timeframe": (
                updated.get("timeframes", [""])[0]
                if updated.get("timeframes")
                else None
            ),
            "start_date": updated.get("start_date"),
            "end_date": updated.get("end_date"),
            "initial_balance": updated.get("initial_balance"),
            "final_balance": updated.get("final_balance"),
            "total_trades": updated.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": updated["created_at"],
            "completed_at": updated.get("completed_at"),
            "alias": updated.get("alias"),
            "description": updated.get("description"),
            "engine_type": updated.get("engine_type"),
            "data_resolution": updated.get("data_resolution"),
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error updating backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update backtest: {str(exc)}",
        )


@backtest_router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest_endpoint(backtest_id: int) -> None:
    """Delete a backtest and all associated data."""
    try:
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        success = db_manager.delete_backtest(backtest_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete backtest {backtest_id}",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error deleting backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backtest: {str(exc)}",
        )


# ========================================
# Portfolio Backtest Endpoints
# ========================================


async def _run_portfolio_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: PortfolioBacktestRequest,
) -> None:
    """Background task to run a portfolio backtest."""
    loop = asyncio.get_event_loop()

    def log_sink(record: Any) -> None:
        log_data = {
            "timestamp": record.time.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "source": record.name,
            "backtest_id": backtest_id,
        }
        with suppress(Exception):
            asyncio.run_coroutine_threadsafe(
                backtest_log_manager.broadcast(backtest_id, log_data), loop
            )

    handler_id = logger.add(log_sink, level="INFO", raw=True)

    try:
        await asyncio.sleep(2.0)
        db_manager.update_backtest_status(backtest_id, "running")

        symbols = _parse_symbols(request.symbols)
        data_mode = _resolve_modelling(request.data_resolution)

        # Load strategy class
        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )

        # Load data and create strategies for each symbol
        data_dict = {}
        strategy_dict = {}
        symbol_specs = {}

        for symbol in symbols:
            # Load data for this symbol
            data, step_data, data_source = _load_data(
                request=BacktestRequest(
                    symbol=symbol,
                    timeframe=request.timeframe,
                    range_by=request.range_by,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    number_of_bars=request.number_of_bars,
                    warmup_by=request.warmup_by,
                    warmup_start_date=request.warmup_start_date,
                    warmup_bars=request.warmup_bars,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    slippage=request.slippage,
                    leverage=request.leverage,
                    data_source=request.data_source,
                    data_resolution=request.data_resolution,
                    lot_size=request.lot_size,
                ),
                symbol=symbol,
                data_mode=data_mode,
                user_id=user_id,
            )

            # Create strategy instance for this symbol
            params = dict(version.get("parameters") or {})
            params["symbol"] = symbol
            params["timeframe"] = request.timeframe
            strategy_instance = strategy_class(params=params)
            if hasattr(strategy_instance, "on_init"):
                strategy_instance.on_init()
            if hasattr(strategy_instance, "on_bar"):
                data = strategy_instance.on_bar(data)

            data_dict[symbol] = data
            strategy_dict[symbol] = strategy_instance

        engine = Engine(backend="sim")
        _seed_engine_account(engine, float(request.initial_capital))

        merged_ticks = []
        tick_model_used = None
        for symbol in symbols:
            _ensure_engine_symbol(engine, symbol)
            ticks_data, tick_model = _generate_ticks_for_backtest(
                engine=engine,
                symbol_name=symbol,
                timeframe=request.timeframe,
                request=BacktestRequest(
                    symbol=symbol,
                    timeframe=request.timeframe,
                    range_by=request.range_by,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    number_of_bars=request.number_of_bars,
                    warmup_by=request.warmup_by,
                    warmup_start_date=request.warmup_start_date,
                    warmup_bars=request.warmup_bars,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    slippage_type=request.slippage_type,
                    slippage=request.slippage,
                    spread_type=request.spread_type,
                    spread=request.spread,
                    spread_min=request.spread_min,
                    spread_max=request.spread_max,
                    leverage=request.leverage,
                    data_source=request.data_source,
                    engine_type="event_driven",
                    data_resolution=request.data_resolution,
                    lot_size=request.lot_size,
                    alias=request.alias,
                    description=request.description,
                ),
                data_mode=data_mode,
                bars_data=data_dict[symbol],
                step_data=None,
            )
            ticks_data = ticks_data.copy()
            ticks_data["symbol"] = symbol
            ticks_data["signal_timeframe"] = request.timeframe
            merged_ticks.append(ticks_data)
            tick_model_used = tick_model

        if not merged_ticks:
            raise ValueError("No merged portfolio ticks generated")

        portfolio_ticks = merged_ticks[0] if len(merged_ticks) == 1 else pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")

        logger.info(
            f"Running portfolio backtest {backtest_id} | "
            f"symbols={symbols} timeframe={request.timeframe} "
            f"allocation={request.allocation_method} ticks_model={tick_model_used}"
        )

        engine.configure_run_schedule(
            positions_every=1,
            pending_orders_every=1,
            account_every=4,
            portfolio_every=4,
            risk_every=4,
        )
        processed = engine.run(
            portfolio_ticks,
            position_size=float(request.lot_size),
            monitor_verbose=False,
            show_progress=False,
        )

        completed_trades = engine.get_completed_trades()
        equity_curve = engine.get_equity_curve()
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)
        if equity_curve:
            db_manager.save_backtest_equity_curve(backtest_id, equity_curve)

        final_balance = float(engine.account_info().get("balance", request.initial_capital) or request.initial_capital)
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=final_balance,
        )

        logger.info(f"Portfolio backtest {backtest_id} completed successfully")
        logger.info(f"Final balance: ${final_balance:,.2f}")
        logger.info(f"Processed ticks: {processed} | Total trades: {len(completed_trades)}")
        engine.client.shutdown()

    except Exception as exc:
        logger.error(f"Portfolio backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
            logger.info(
                f"WebSocket handler removed for portfolio backtest {backtest_id}"
            )
        except Exception as exc:
            logger.warning(f"Error removing WebSocket handler: {exc}")

        try:
            await asyncio.sleep(5.0)
            await backtest_log_manager.clear_buffer(backtest_id)
            logger.info(f"Log buffer cleared for portfolio backtest {backtest_id}")
        except Exception as exc:
            logger.warning(f"Error clearing log buffer: {exc}")

        logger.info(f"Portfolio backtest task completed for backtest {backtest_id}")


@backtest_router.post("/portfolio/run/{strategy_id}", response_model=PortfolioBacktestResponse)
async def run_portfolio_backtest(
    strategy_id: int,
    request: PortfolioBacktestRequest,
    background_tasks: BackgroundTasks,
    authorization: Annotated[Optional[str], Header()] = None,
) -> PortfolioBacktestResponse:
    """Run a portfolio backtest with multiple symbols."""
    try:
        user_id = get_user_id_from_token(authorization)
        symbols = _parse_symbols(request.symbols)

        strategy = db_manager.get_strategy(strategy_id)
        if not strategy or not strategy.get("active_version_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy or active version not found",
            )

        version_id = int(strategy["active_version_id"])
        start_dt = _parse_request_date(request.start_date) or datetime.utcnow()
        end_dt = _parse_request_date(request.end_date) or datetime.utcnow()

        # Create backtest run in database
        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",
            start_date=start_dt,
            end_date=end_dt,
            engine_type="event_driven",
            data_resolution=request.data_resolution or "trading_timeframe",
            config_hash=str(hash((strategy_id, tuple(symbols), request.timeframe))),
            symbols=symbols,
            timeframes=[request.timeframe],
            initial_balance=request.initial_capital,
            alias=request.alias,
            description=request.description,
            strategy_version_id=version_id,
            user_id=user_id,
        )

        # Add background task
        background_tasks.add_task(
            _run_portfolio_backtest_task,
            backtest_id=backtest_id,
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
            request=request,
        )

        backtest_run = db_manager.get_backtest_run(backtest_id)
        if backtest_run is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "status": backtest_run["status"],
            "portfolio_name": backtest_run["strategy_name"],
            "symbols": symbols,
            "timeframe": request.timeframe,
            "start_date": backtest_run["start_date"],
            "end_date": backtest_run["end_date"],
            "initial_balance": backtest_run["initial_balance"],
            "final_balance": backtest_run.get("final_balance"),
            "total_return": None,
            "total_return_pct": None,
            "total_trades": backtest_run.get("total_trades"),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown_pct": None,
            "created_at": backtest_run["created_at"],
            "completed_at": backtest_run.get("completed_at"),
            "allocation_method": request.allocation_method or "equal_weight",
            "asset_results": None,
        }

        return PortfolioBacktestResponse(**response_data)

    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning(f"Invalid portfolio backtest request: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Error starting portfolio backtest: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start portfolio backtest: {str(exc)}",
        )

