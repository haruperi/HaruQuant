"""Backtest API routes and helpers."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from api.auth_utils import get_user_id_from_token
from api.websocket import backtest_log_manager
from haruquant.data import MT5Client
from data.database.sqlite.database_operations import DatabaseManager
from haruquant.strategy import storage
from haruquant.strategy import assert_strategy_allowed
from haruquant.simulation import Engine
from haruquant.execution import core
from haruquant.data import load_dukascopy
from haruquant.data import TicksGenerator
from haruquant.data import DataValidator
from haruquant.utils import logger
from haruquant.analytics import build_overview_payload

from haruquant.simulation import _generate_ticks_for_backtest, _normalize_position_sizing_method, _resolve_engine_type, _resolve_modelling, _resolve_tick_generator_config

import haruquant as hqt

router = APIRouter()
db_manager = DatabaseManager()
AUTH_HEADER = Header(None)


def _map_request_to_config(
    request: Union[BacktestRequest, PortfolioBacktestRequest],
    strategy_name: str,
    params: Dict[str, Any],
    user_id: int,
    symbols: Optional[List[str]] = None,
    backtest_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Map flat API request to nested SimulationConfig structure."""
    if symbols is None:
        # Fallback to single symbol from request if not provided
        symbols = [getattr(request, "symbol", "")]

    return {
        "engine_type": _resolve_engine_type(request.engine_type),
        "account": {
            "initial_balance": float(request.initial_capital),
            "commission": float(request.commission),
            "leverage": int(request.leverage),
        },
        "data": {
            "source": str(request.data_source or "mt5").lower(),
            "symbols": symbols,
            "timeframe": request.timeframe,
            "start": request.start_date,
            "end": request.end_date,
            "warmup_start": request.warmup_start_date,
        },
        "strategy": {
            "name": strategy_name,
            "params": params,
        },
        "execution": {
            "tick_model": _resolve_tick_generator_config(request, _resolve_modelling(request.data_resolution))[0],
            "spread_model": _resolve_tick_generator_config(request, _resolve_modelling(request.data_resolution))[1],
            "slippage_model": str(request.slippage_type or "fixed"),
            "slippage_points": float(request.slippage or 0),
            "position_size": {
                "type": _normalize_position_sizing_method(request.position_sizing_method),
                "lot_size": float(request.lot_size),
                # Add extra fields for dynamic sizing if needed
                "risk_percent": float(getattr(request, "risk_percent", 1.0)),
            },
        },
        "reporting": {
            "save_to_db": True,
            "user_id": user_id,
            "backtest_id": backtest_id,
            "alias": request.alias,
            "description": request.description,
        },
    }

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


class BacktestOverviewResponse(BaseModel):
    """Backend-computed overview payload for a backtest."""

    summary: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Dict[str, Any]]
    returns: Dict[str, Dict[str, Any]] = {}
    ratios: Dict[str, Dict[str, Any]] = {}
    risks: Dict[str, Dict[str, Any]] = {}
    drawdowns: Dict[str, Dict[str, Any]] = {}
    distributions: Dict[str, Dict[str, Any]] = {}
    efficiency: Dict[str, Dict[str, Any]] = {}
    benchmark: Dict[str, Dict[str, Any]] = {}
    validation: Dict[str, Dict[str, Any]] = {}
    dashboard: Dict[str, Any] = {}
    scorecard: Dict[str, Any] = {}
    equity_curves: Dict[str, List[Dict[str, Any]]]
    charts: Dict[str, List[Dict[str, Any]]]


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
    engine_type: Optional[str] = "event_driven"
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


def _load_strategy_class(user_id: int, strategy_id: int, version_id: int):
    assert_strategy_allowed(strategy_id, "backtest", db_manager=db_manager)
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


async def _run_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: BacktestRequest,
) -> None:
    """Background task to run a backtest using the high-performance Portfolio API."""
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
        await asyncio.sleep(1.0)
        db_manager.update_backtest_status(backtest_id, "running")

        # Load strategy class from DB
        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )
        
        # Register strategy so Portfolio.run can find it by name
        from haruquant.simulation import register_strategy
        strategy_name = f"db_strategy_{strategy_id}_{version_id}"
        register_strategy(strategy_name, strategy_class)

        # Prepare configuration
        config = _map_request_to_config(
            request=request,
            strategy_name=strategy_name,
            params=version.get("parameters", {}),
            user_id=user_id,
            backtest_id=backtest_id,
        )
        
        # Run high-performance simulation (Automatic DB persistence enabled in config)
        logger.info(f"Starting batch backtest {backtest_id} using hqt.Portfolio.run")
        portfolio = hqt.Portfolio.run(config, user_id=user_id)
        
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=float(portfolio.final_value),
        )
        logger.info(
            f"Backtest {backtest_id} completed successfully | "
            f"trades={len(portfolio.trades)} final_equity={portfolio.final_value:.2f}"
        )

    except Exception as exc:
        logger.exception(f"Backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
        except Exception:
            pass

        try:
            await asyncio.sleep(2.0)
            await backtest_log_manager.clear_buffer(backtest_id)
        except Exception:
            pass


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

        snapshot = db_manager.get_backtest_snapshot(backtest_id)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        metadata = snapshot.get("metadata", {}) or {}
        result = snapshot.get("result", {}) or {}

        response_data = {
            "backtest_id": snapshot["backtest_id"],
            "strategy_version_id": metadata.get("strategy_version_id"),
            "status": metadata.get("status", "completed"),
            "strategy_name": metadata.get("strategy_name") or metadata.get("strategy", {}).get("name"),
            "symbol": symbol,
            "timeframe": request.timeframe,
            "start_date": metadata.get("data", {}).get("start") or metadata.get("start_date"),
            "end_date": metadata.get("data", {}).get("end") or metadata.get("end_date"),
            "initial_balance": metadata.get("account", {}).get("initial_balance", metadata.get("initial_balance")),
            "final_balance": metadata.get("final_balance"),
            "total_trades": len((result.get("trades", []) or [])),
            "win_rate": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("win_rate_pct"),
            "profit_factor": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("profit_factor"),
            "sharpe_ratio": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("sharpe_ratio"),
            "max_drawdown": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("max_drawdown_pct"),
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
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
        snapshot = db_manager.get_backtest_snapshot(backtest_id)
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        metadata = snapshot.get("metadata", {}) or {}
        result = snapshot.get("result", {}) or {}
        result_trades = result.get("trades", []) or []

        response_data = {
            "backtest_id": snapshot["backtest_id"],
            "strategy_id": metadata.get("strategy_id"),
            "strategy_version_id": metadata.get("strategy_version_id"),
            "status": metadata.get("status", "completed"),
            "strategy_name": metadata.get("strategy_name") or metadata.get("strategy", {}).get("name"),
            "symbol": ",".join(metadata.get("data", {}).get("symbols", []) or metadata.get("symbols", []) or []) or None,
            "timeframe": metadata.get("data", {}).get("timeframe") or (metadata.get("timeframes") or [None])[0],
            "start_date": metadata.get("data", {}).get("start") or metadata.get("start_date"),
            "end_date": metadata.get("data", {}).get("end") or metadata.get("end_date"),
            "initial_balance": metadata.get("account", {}).get("initial_balance", metadata.get("initial_balance")),
            "final_balance": metadata.get("final_balance"),
            "total_trades": len(result_trades),
            "win_rate": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("win_rate_pct"),
            "profit_factor": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("profit_factor"),
            "sharpe_ratio": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("sharpe_ratio"),
            "max_drawdown": (snapshot.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("max_drawdown_pct"),
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
            "alias": metadata.get("reporting", {}).get("alias", metadata.get("alias")),
            "description": metadata.get("reporting", {}).get("description", metadata.get("description")),
            "engine_type": metadata.get("engine_type"),
            "data_resolution": metadata.get("data_resolution"),
            "trades": result_trades,
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


@router.get("/{backtest_id}/overview", response_model=BacktestOverviewResponse)
async def get_backtest_overview(backtest_id: int) -> BacktestOverviewResponse:
    """Get the backend-computed performance overview for a backtest."""
    try:
        payload = db_manager.get_backtest_overview_snapshot(backtest_id)
        
        # Check if the cached payload is missing the new analytics categories or processed_ticks
        is_stale = (
            payload is None 
            or "returns" not in payload 
            or not payload.get("returns")
            or "dashboard" not in payload
            or "scorecard" not in payload
            or "validation" not in payload
            or "processed_ticks" not in (payload.get("summary", {}).get("all", {}) or {})
        )
        
        if is_stale:
            snapshot = db_manager.get_backtest_snapshot(backtest_id)
            if not snapshot:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Backtest {backtest_id} not found",
                )

            metadata = snapshot.get("metadata", {}) or {}
            result = snapshot.get("result", {}) or {}
            trades = result.get("trades", []) or []
            
            # Force re-calculation of the full comprehensive suite
            payload = build_overview_payload(
                trades,
                initial_balance=float(
                    metadata.get("account", {}).get("initial_balance")
                    or metadata.get("initial_balance")
                    or 0.0
                ),
                start_time=metadata.get("data", {}).get("start") or metadata.get("start_date"),
                end_time=metadata.get("data", {}).get("end") or metadata.get("end_date"),
                equity_curve_records=result.get("equity_curve", []) or [],
                summary_overrides={
                    "processed_ticks": result.get("processed_ticks") or metadata.get("tick_count")
                }
            )
            
            # Optional: Update the database with the new full payload if it was completed
            if metadata.get("status") == "completed" and payload:
                db_manager.save_backtest_snapshot(backtest_id, analytics={"overview": payload})
        
        # Ensure processed_ticks is available in the final response even if not in the cached payload
        if payload and "summary" in payload and "all" in payload["summary"]:
            if not payload["summary"]["all"].get("processed_ticks"):
                snapshot = db_manager.get_backtest_snapshot(backtest_id)
                if snapshot:
                    meta = snapshot.get("metadata", {}) or {}
                    payload["summary"]["all"]["processed_ticks"] = meta.get("tick_count") or meta.get("processed_ticks")
                
        return BacktestOverviewResponse(**payload)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting backtest overview: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backtest overview: {str(exc)}",
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
        snapshot = db_manager.get_backtest_snapshot(backtest_id)
        if not snapshot:
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

        updated = db_manager.get_backtest_snapshot(backtest_id)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load backtest {backtest_id}",
            )

        metadata = updated.get("metadata", {}) or {}
        result = updated.get("result", {}) or {}

        response_data = {
            "backtest_id": updated["backtest_id"],
            "strategy_id": metadata.get("strategy_id"),
            "strategy_version_id": metadata.get("strategy_version_id"),
            "status": metadata.get("status", "completed"),
            "strategy_name": metadata.get("strategy_name") or metadata.get("strategy", {}).get("name"),
            "symbol": ",".join(metadata.get("data", {}).get("symbols", []) or metadata.get("symbols", []) or []) or None,
            "timeframe": metadata.get("data", {}).get("timeframe") or (metadata.get("timeframes") or [None])[0],
            "start_date": metadata.get("data", {}).get("start") or metadata.get("start_date"),
            "end_date": metadata.get("data", {}).get("end") or metadata.get("end_date"),
            "initial_balance": metadata.get("account", {}).get("initial_balance", metadata.get("initial_balance")),
            "final_balance": metadata.get("final_balance"),
            "total_trades": len((result.get("trades", []) or [])),
            "win_rate": (updated.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("win_rate_pct"),
            "profit_factor": (updated.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("profit_factor"),
            "sharpe_ratio": (updated.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("sharpe_ratio"),
            "max_drawdown": (updated.get("analytics", {}) or {}).get("summary", {}).get("all", {}).get("max_drawdown_pct"),
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
            "alias": metadata.get("reporting", {}).get("alias", metadata.get("alias")),
            "description": metadata.get("reporting", {}).get("description", metadata.get("description")),
            "engine_type": metadata.get("engine_type"),
            "data_resolution": metadata.get("data_resolution"),
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
        snapshot = db_manager.get_backtest_snapshot(backtest_id)
        if not snapshot:
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
    """Background task to run a portfolio backtest using the high-performance Portfolio API."""
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
        await asyncio.sleep(1.0)
        db_manager.update_backtest_status(backtest_id, "running")

        symbols = _parse_symbols(request.symbols)

        # Load strategy class from DB
        version, strategy_meta, strategy_class = _load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
        )
        
        # Register strategy so Portfolio.run can find it
        from haruquant.simulation import register_strategy
        strategy_name = f"db_strategy_{strategy_id}_{version_id}"
        register_strategy(strategy_name, strategy_class)

        # Prepare configuration
        config = _map_request_to_config(
            request=request,
            strategy_name=strategy_name,
            params=version.get("parameters", {}),
            user_id=user_id,
            symbols=symbols,
            backtest_id=backtest_id,
        )
        
        # Run high-performance portfolio simulation (Automatic DB persistence enabled in config)
        logger.info(f"Starting portfolio backtest {backtest_id} using hqt.Portfolio.run")
        portfolio = hqt.Portfolio.run(config, user_id=user_id)
        
        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=float(portfolio.final_value),
        )

        logger.info(
            f"Portfolio backtest {backtest_id} completed successfully | "
            f"trades={len(portfolio.trades)} final_equity={portfolio.final_value:,.2f}"
        )

    except Exception as exc:
        logger.exception(f"Portfolio backtest {backtest_id} failed: {exc}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        try:
            logger.remove(handler_id)
        except Exception:
            pass

        try:
            await asyncio.sleep(2.0)
            await backtest_log_manager.clear_buffer(backtest_id)
        except Exception:
            pass


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

        snapshot = db_manager.get_backtest_snapshot(backtest_id)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        metadata = snapshot.get("metadata", {}) or {}
        result = snapshot.get("result", {}) or {}

        response_data = {
            "backtest_id": snapshot["backtest_id"],
            "status": metadata.get("status", "completed"),
            "portfolio_name": metadata.get("strategy_name") or metadata.get("strategy", {}).get("name"),
            "symbols": symbols,
            "timeframe": request.timeframe,
            "start_date": metadata.get("data", {}).get("start") or metadata.get("start_date"),
            "end_date": metadata.get("data", {}).get("end") or metadata.get("end_date"),
            "initial_balance": metadata.get("account", {}).get("initial_balance", metadata.get("initial_balance")),
            "final_balance": metadata.get("final_balance"),
            "total_return": None,
            "total_return_pct": None,
            "total_trades": len((result.get("trades", []) or [])),
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown_pct": None,
            "created_at": metadata.get("created_at"),
            "completed_at": metadata.get("completed_at"),
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

