"""Backtest API routes and helpers."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from backend.api.legacy.auth_utils import get_user_id_from_token
from backend.api.legacy.websocket import backtest_log_manager
from apps.mt5.client import MT5Client
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.trading import Engine, core
from apps.utils.data_getters import load_dukascopy
from apps.utils.data_manipulator import TicksGenerator
from apps.utils.data_validator import DataValidator
from apps.utils.logger import logger

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)

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
    fractional_factor: float = 2.0
    use_dynamic_stop_loss: bool = False
    atr_multiplier: float = 2.0
    win_rate: float = 0.55
    avg_win: float = 150.0
    avg_loss: float = 100.0
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
    fractional_factor: float = 2.0
    use_dynamic_stop_loss: bool = False
    atr_multiplier: float = 2.0
    win_rate: float = 0.55
    avg_win: float = 150.0
    avg_loss: float = 100.0
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


def _normalize_position_sizing_method(value: Optional[str]) -> str:
    raw = str(value or "fixed_lot").strip().lower().replace("-", "_")
    mapping = {
        "fixed_lot": "fixed_lot",
        "fixed_percent": "fixed_risk",
        "fixed_risk": "fixed_risk",
        "milestone": "milestone",
        "kelly_criterion": "kelly",
        "kelly": "kelly",
        "volatility_adjusted_atr": "volatility",
        "volatility": "volatility",
        "fixed_fractional": "fixed_fractional",
    }
    return mapping.get(raw, "fixed_lot")


def _build_position_sizing_config(request: BacktestRequest, method: str) -> dict:
    if method == "fixed_risk":
        return {
            "risk_percent": float(request.risk_percent),
            "use_dynamic_stop_loss": bool(getattr(request, "use_dynamic_stop_loss", False)),
        }
    if method == "milestone":
        return {
            "initial_balance": float(request.initial_capital),
            "base_lot_size": float(request.base_lot_size),
            "milestone_amount": float(request.milestone_amount),
            "lot_increment": float(request.lot_increment),
        }
    if method == "kelly":
        return {
            "kelly_fraction_limit": float(request.kelly_fraction_limit),
            "win_rate": float(getattr(request, "win_rate", 0.55)),
            "avg_win": float(getattr(request, "avg_win", 150.0)),
            "avg_loss": float(getattr(request, "avg_loss", 100.0)),
        }
    if method == "volatility":
        return {
            "risk_percent": float(request.risk_percent),
            "atr_multiplier": float(getattr(request, "atr_multiplier", 2.0)),
        }
    if method == "fixed_fractional":
        return {
            "fraction": float(getattr(request, "fractional_factor", request.fraction)),
        }
    return {"lot_size": float(request.lot_size)}


def _configure_backtest_engine(
    engine: Engine,
    request: BacktestRequest,
    historical_data=None,
) -> None:
    account = engine.account_info()
    account["balance"] = float(request.initial_capital)
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = float(request.initial_capital)
    account["margin"] = 0.0
    account["margin_free"] = float(request.initial_capital)
    account["margin_level"] = 0.0
    account["commission"] = float(request.commission)
    account["leverage"] = int(request.leverage)

    engine.state.execution_settings = core.DotDict(
        {
            "slippage_model": str(request.slippage_type or "fixed"),
            "slippage_points": float(request.slippage or 0),
            "slippage_min": float(request.slippage_min or 0),
            "slippage_max": float(request.slippage_max or 0),
        }
    )

    method = _normalize_position_sizing_method(request.position_sizing_method)
    if method == "fixed_lot":
        engine.configure_position_sizing(enabled=False)
        return

    engine.configure_position_sizing(
        enabled=True,
        position_sizing_method=method,
        position_sizing_config=_build_position_sizing_config(request, method),
        historical_data=historical_data or {},
    )


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
        _configure_backtest_engine(
            engine,
            request,
            historical_data={symbol: {request.timeframe: data.copy()}},
        )
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


@router.post("/run/{strategy_id}", response_model=BacktestResponse)
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


@router.get("/strategy/{strategy_id}", response_model=List[BacktestResponse])
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


@router.get("/{backtest_id}", response_model=BacktestResponse)
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


@router.websocket("/ws/{backtest_id}/logs")
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


@router.get("/", response_model=List[BacktestResponse])
async def list_all_backtests(
    authorization: str = AUTH_HEADER, limit: int = 100
) -> List[BacktestResponse]:
    """List all backtests across all strategies."""
    try:
        user_id = get_user_id_from_token(authorization)
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


@router.put("/{backtest_id}", response_model=BacktestResponse)
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


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
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
        _configure_backtest_engine(
            engine,
            request,
            historical_data={
                symbol_name: {request.timeframe: symbol_data.copy()}
                for symbol_name, symbol_data in data_dict.items()
            },
        )

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


@router.post("/portfolio/run/{strategy_id}", response_model=PortfolioBacktestResponse)
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

