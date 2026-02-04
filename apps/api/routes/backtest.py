"""Backtest routes wired to the simulator backend."""

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel

from apps.api.auth_utils import get_user_id_from_token
from apps.api.websocket import backtest_log_manager
from apps.logger import logger
from apps.mt5.client import MT5Client
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.simulator import TradeSimulator
from apps.sqlite import SQLiteDatabase
from apps.strategy import storage
from apps.utils.data_getters import load_dukascopy
from apps.utils.data_validator import DataValidator

router = APIRouter()
db_manager = SQLiteDatabase()


class BacktestRequest(BaseModel):
    """Request payload for running a backtest."""

    symbol: str
    timeframe: str
    range_by: Optional[str] = "dates"  # "dates" or "bars"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    number_of_bars: Optional[int] = None
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


def _parse_request_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


def _parse_symbol(value: str) -> str:
    symbols = [s.strip().upper() for s in value.split(",") if s.strip()]
    if not symbols:
        raise ValueError("Symbol is required")
    if len(symbols) > 1:
        raise ValueError("Simulator backtests support one symbol at a time")
    return symbols[0]


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
        return client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=request.number_of_bars,
        )
    return client.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        date_from=_parse_request_date(request.start_date),
        date_to=_parse_request_date(request.end_date),
    )


def _load_mt5_ticks(client: MT5Client, symbol: str, request: BacktestRequest):
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        tick_count = request.number_of_bars * 100
        return client.get_ticks(symbol=symbol, count=tick_count)
    return client.get_ticks(
        symbol=symbol,
        start=_parse_request_date(request.start_date),
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
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                count=request.number_of_bars,
            )
        else:
            data = load_dukascopy(
                symbol=symbol,
                timeframe=request.timeframe,
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if data is None or data.empty:
            raise ValueError("No trading timeframe data loaded from Dukascopy")
        data = DataValidator.prepare_data(data)

        if data_mode == "real_ticks":
            raise ValueError("Real ticks are not available for Dukascopy source")
        if data_mode in {"m1_ohlc", "synthetic_ticks"}:
            step_data = load_dukascopy(
                symbol=symbol,
                timeframe="M1",
                start_date=request.start_date,
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

        creds = db_manager.get_mt5_credentials(user_id)
        client = MT5Client()
        if creds:
            client.connect(
                path=creds.get("path", ""),
                login=creds.get("login", 0),
                password=creds.get("password", ""),
                server=creds.get("server", ""),
            )

        account_info = AccountInfoSimulator(
            balance=float(request.initial_capital),
            equity=float(request.initial_capital),
            margin_free=float(request.initial_capital),
        )
        symbol_info = SymbolInfoSimulator.from_mt5_symbol(symbol)
        symbol_info.symbol = symbol

        simulator = TradeSimulator(
            simulator_name=f"Backtest {backtest_id}",
            mt5_client=client,
            account_info=account_info,
            symbols={symbol: symbol_info},
        )

        simulator.trade.SetExpertMagicNumber(10001)
        if request.slippage_type == "fixed":
            simulator.trade.SetDeviationInPoints(int(request.slippage or 0))

        logger.info(
            f"Running simulator backtest {backtest_id} | "
            f"symbol={symbol} timeframe={request.timeframe} "
            f"engine={engine_type} mode={data_mode} source={data_source}"
        )

        # ----------------------------
        # Vectorized Engine Support
        # ----------------------------
        simulator.run(
            data=data,
            strategy=strategy_instance,
            symbol=symbol,
            volume=float(request.lot_size),
            verbose=False,
            save_db=False,
            step_data=step_data,
            data_modelling=data_mode,
            engine_type=engine_type,
        )

        completed_trades = simulator._completed_trades
        if completed_trades:
            db_manager.save_backtest_trades(backtest_id, completed_trades)

        db_manager.update_backtest_status(
            backtest_id,
            "completed",
            final_balance=float(simulator._account_data.balance),
        )
        logger.info(f"Backtest {backtest_id} completed successfully")

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
