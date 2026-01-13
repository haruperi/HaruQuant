"""Backtest routes for running and managing simulations."""

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

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
from apps.backtest import EventDrivenEngine, VectorizedEngine
from apps.backtest.persistence import BacktestDatabase
from apps.backtest.portfolio import (
    AssetClass,
    AssetSpecification,
    PortfolioEngine,
    PortfolioStrategy,
    create_asset_spec_crypto,
    create_asset_spec_forex,
)
from apps.logger import logger
from apps.risk.position_sizing import PositionSizer
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.utils.data_getters import load_dukascopy

router = APIRouter()
db_manager = DatabaseManager()
backtest_db = BacktestDatabase()


# --- Pydantic Models ---


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
    slippage_type: Optional[str] = "fixed"  # "fixed" or "variable"
    slippage: int = 0  # Fixed slippage in points
    slippage_min: int = 0  # Min slippage in points for variable
    slippage_max: int = 10  # Max slippage in points for variable
    spread_type: Optional[str] = "use-broker"  # "use-broker", "fixed", or "variable"
    spread: int = 20  # Fixed spread in points
    spread_min: int = 10  # Min spread in points for variable
    spread_max: int = 50  # Max spread in points for variable
    leverage: int = 100
    data_source: Optional[str] = "dukascopy"
    engine_type: Optional[str] = "vectorized"
    data_resolution: Optional[str] = "timeframe"  # tick, m1, or timeframe
    # Position Sizing / Money Management
    position_sizing_method: Optional[str] = (
        "fixed_lot"  # fixed_lot, milestone, fixed_risk, kelly, volatility, fixed_fractional
    )
    lot_size: float = 0.1  # for fixed_lot
    risk_percent: float = 1.0  # for fixed_risk, volatility
    base_lot_size: float = 0.1  # for milestone
    milestone_amount: float = 3000  # for milestone
    lot_increment: float = 0.2  # for milestone
    kelly_fraction_limit: float = 0.25  # for kelly
    fraction: float = 2.0  # for fixed_fractional
    alias: Optional[str] = None
    description: Optional[str] = None


class BacktestResponse(BaseModel):
    """Response model for backtest runs."""

    backtest_id: int  # Auto-increment ID
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


# --- Helper Functions ---


def _resolve_resolution(request: BacktestRequest) -> tuple[str, str, bool]:
    resolution = (request.data_resolution or "timeframe").lower()
    data_step_mode = "trading_timeframe"
    if resolution == "m1":
        data_step_mode = "m1_bars"
    elif resolution == "tick":
        data_step_mode = "tick"

    need_high_res = resolution in ["m1", "tick"]
    return resolution, data_step_mode, need_high_res


def _build_position_sizer(request: BacktestRequest) -> PositionSizer:
    """Build PositionSizer from request parameters."""
    method = request.position_sizing_method or "fixed_lot"

    # Build config based on method
    config: Dict[str, Any] = {
        "initial_balance": request.initial_capital,
    }

    if method == "fixed_lot":
        config["lot_size"] = request.lot_size
    elif method == "fixed_risk":
        config["risk_percent"] = request.risk_percent
    elif method == "milestone":
        config["initial_balance"] = request.initial_capital
        config["base_lot_size"] = request.base_lot_size
        config["milestone_amount"] = request.milestone_amount
        config["lot_increment"] = request.lot_increment
    elif method == "kelly":
        config["kelly_fraction_limit"] = request.kelly_fraction_limit
    elif method == "volatility":
        config["risk_percent"] = request.risk_percent
    elif method == "fixed_fractional":
        config["fraction"] = request.fraction

    logger.info(f"Position sizing: method={method}, config={config}")
    return PositionSizer(method=method, config=config)


def _parse_request_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


def _timeframe_to_minutes(timeframe: str) -> int:
    mapping = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
        "W1": 10080,
        "MN1": 43200,
    }
    tf = timeframe.strip().upper()
    if tf not in mapping:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return mapping[tf]


def _fetch_mt5_signal_data(client, request):
    logger.info(f"Fetching Signal Data ({request.timeframe})...")
    if request.range_by == "bars":
        if request.number_of_bars is None:
            raise ValueError("number_of_bars is required when range_by='bars'")
        logger.info(f"Loading {request.number_of_bars} bars")
        data = client.get_bars(
            symbol=request.symbol,
            timeframe=request.timeframe,
            count=request.number_of_bars,
        )
    else:
        data = client.get_bars(
            symbol=request.symbol,
            timeframe=request.timeframe,
            date_from=_parse_request_date(request.start_date),
            date_to=_parse_request_date(request.end_date),
        )
    return data


def _fetch_mt5_execution_data(client, request, resolution):
    if resolution == "m1":
        if request.range_by == "bars":
            tf_minutes = _timeframe_to_minutes(request.timeframe)
            if request.number_of_bars is None:
                raise ValueError("number_of_bars is required when range_by='bars'")
            m1_count = request.number_of_bars * tf_minutes
            return client.get_bars(
                symbol=request.symbol,
                timeframe="M1",
                count=m1_count,
            )
        return client.get_bars(
            symbol=request.symbol,
            timeframe="M1",
            date_from=_parse_request_date(request.start_date),
            date_to=_parse_request_date(request.end_date),
        )

    if resolution == "tick":
        if request.range_by == "bars":
            if request.number_of_bars is None:
                raise ValueError("number_of_bars is required when range_by='bars'")
            tick_count = request.number_of_bars * 100
            return client.get_ticks(
                symbol=request.symbol,
                count=tick_count,
            )
        return client.get_ticks(
            symbol=request.symbol,
            start=_parse_request_date(request.start_date),
            end=_parse_request_date(request.end_date),
        )

    return None


def _prepare_mt5_execution_data(execution_data, resolution, data_step_mode):
    from apps.utils.data_validator import DataValidator

    if execution_data is None or execution_data.empty:
        logger.warning(
            "Failed to load execution data, falling back to timeframe resolution"
        )
        return None, "trading_timeframe"

    if resolution == "m1":
        execution_data = DataValidator.prepare_data(execution_data)
    elif resolution == "tick":
        execution_data.columns = [str(c).lower() for c in execution_data.columns]

    logger.info(f"Loaded {len(execution_data)} execution records")
    return execution_data, data_step_mode


def _load_mt5_data(
    request: BacktestRequest,
    user_id: int,
    resolution: str,
    need_high_res: bool,
    data_step_mode: str,
):
    from apps.mt5.client import MT5Client

    credentials = db_manager.get_mt5_credentials(user_id)
    if credentials:
        client = MT5Client(
            path=credentials.get("path", ""),
            login=credentials.get("login", 0),
            password=credentials.get("password", ""),
            server=credentials.get("server", ""),
        )
    else:
        logger.warning(f"No MT5 credentials found for user {user_id}, using defaults")
        client = MT5Client()
    if not client.initialize():
        raise RuntimeError("Failed to connect to MT5")

    data = None
    execution_data = None

    try:
        data = _fetch_mt5_signal_data(client, request)

        if data is None or data.empty:
            raise ValueError(f"No {request.timeframe} data found for {request.symbol}")

        from apps.utils.data_validator import DataValidator

        data = DataValidator.prepare_data(data)

        if need_high_res:
            logger.info(f"Fetching Execution Data ({resolution})...")
            execution_data = _fetch_mt5_execution_data(client, request, resolution)
            execution_data, data_step_mode = _prepare_mt5_execution_data(
                execution_data, resolution, data_step_mode
            )

    finally:
        client.shutdown()

    return data, execution_data, data_step_mode


def _load_dukascopy_data(
    request: BacktestRequest, need_high_res: bool, data_step_mode: str
):
    data = None
    execution_data = None

    if request.range_by == "bars":
        logger.info(f"Loading {request.number_of_bars} bars from Dukascopy")
        data = load_dukascopy(
            symbol=request.symbol,
            timeframe=request.timeframe,
            count=request.number_of_bars,
        )
    else:
        data = load_dukascopy(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
        )

    if need_high_res and data is not None:
        logger.info("Fetching Dukascopy M1 data for execution...")
        execution_data = load_dukascopy(
            symbol=request.symbol,
            timeframe="M1",
            start_date=request.start_date,
            end_date=request.end_date,
        )

        if execution_data is not None and not execution_data.empty:
            logger.info(f"Loaded {len(execution_data)} Dukascopy M1 bars for execution")
        else:
            logger.warning("Failed to load Dukascopy execution data")
            data_step_mode = "trading_timeframe"
            execution_data = None

    return data, execution_data, data_step_mode


def _parse_symbols(symbol_str: str) -> List[str]:
    """Parse comma-separated symbols into a list."""
    symbols = [s.strip().upper() for s in symbol_str.split(",") if s.strip()]
    return symbols


def _is_portfolio_backtest(symbol_str: str) -> bool:
    """Check if this is a multi-symbol portfolio backtest."""
    return len(_parse_symbols(symbol_str)) > 1


def _create_asset_spec(symbol: str, request: BacktestRequest) -> AssetSpecification:
    """Create asset specification based on symbol type."""
    symbol_upper = symbol.upper()

    # Detect asset type from symbol
    if symbol_upper.endswith("USD") and len(symbol_upper) == 6:
        # Forex pair like EURUSD, GBPUSD
        is_jpy = "JPY" in symbol_upper
        return AssetSpecification(
            symbol=symbol,
            asset_class=AssetClass.FOREX,
            contract_size=100000,
            point=0.01 if is_jpy else 0.0001,
            commission=request.commission,
            leverage=request.leverage,
            margin_requirement=1.0 / request.leverage if request.leverage > 0 else 0.01,
            max_position_pct=0.34,
            description=f"{symbol} Forex Pair",
        )
    elif symbol_upper in ["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD"]:
        # Crypto
        return create_asset_spec_crypto(
            symbol=symbol,
            commission=request.commission,
            leverage=request.leverage,
        )
    else:
        # Default to forex-like specification
        return create_asset_spec_forex(
            symbol=symbol,
            commission=request.commission,
            leverage=request.leverage,
        )


def _load_symbol_data_mt5(
    symbol: str,
    request: BacktestRequest,
    user_id: int,
) -> Optional[Any]:
    from apps.mt5.client import MT5Client
    from apps.utils.data_validator import DataValidator

    credentials = db_manager.get_mt5_credentials(user_id)
    if credentials:
        client = MT5Client(
            path=credentials.get("path", ""),
            login=credentials.get("login", 0),
            password=credentials.get("password", ""),
            server=credentials.get("server", ""),
        )
    else:
        client = MT5Client()

    if not client.initialize():
        logger.warning(f"Failed to connect to MT5 for {symbol}")
        return None

    try:
        if request.range_by == "bars":
            if request.number_of_bars is None:
                raise ValueError("number_of_bars is required when range_by='bars'")
            data = client.get_bars(
                symbol=symbol,
                timeframe=request.timeframe,
                count=request.number_of_bars,
            )
        else:
            data = client.get_bars(
                symbol=symbol,
                timeframe=request.timeframe,
                date_from=_parse_request_date(request.start_date),
                date_to=_parse_request_date(request.end_date),
            )

        if data is not None and not data.empty:
            return DataValidator.prepare_data(data)
    finally:
        client.shutdown()

    return None


def _load_symbol_data_dukascopy(
    symbol: str,
    request: BacktestRequest,
) -> Optional[Any]:
    if request.range_by == "bars":
        return load_dukascopy(
            symbol=symbol,
            timeframe=request.timeframe,
            count=request.number_of_bars,
        )

    return load_dukascopy(
        symbol=symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
    )


def _load_symbol_data(
    symbol: str,
    request: BacktestRequest,
    user_id: int,
    data_source: str,
) -> Optional[Any]:
    """Load data for a single symbol."""
    try:
        if data_source.lower() in ["metatrader5", "mt5"]:
            return _load_symbol_data_mt5(symbol, request, user_id)

        return _load_symbol_data_dukascopy(symbol, request)
    except Exception as e:
        logger.warning(f"Failed to load data for {symbol}: {e}")

    return None


def _load_portfolio_data(
    symbols: List[str],
    request: BacktestRequest,
    user_id: int,
) -> Dict[str, Any]:
    """Load data for multiple symbols."""
    data_source = request.data_source or "dukascopy"
    datasets = {}

    logger.info(f"Loading portfolio data for {len(symbols)} symbols from {data_source}")

    for symbol in symbols:
        data = _load_symbol_data(symbol, request, user_id, data_source)
        if data is not None and len(data) > 0:
            datasets[symbol] = data
            logger.info(f"  {symbol}: {len(data):,} bars loaded")
        else:
            logger.warning(f"  {symbol}: Failed to load data")

    return datasets


def _load_backtest_data(request: BacktestRequest, user_id: int):
    data_source = request.data_source or "dukascopy"
    resolution, data_step_mode, need_high_res = _resolve_resolution(request)

    logger.info(
        f"Loading data from {data_source}: {request.symbol} {request.timeframe}"
    )
    logger.info(
        f"Loading data from {data_source}: {request.symbol} {request.timeframe} "
        f"(Resolution: {resolution})"
    )

    if data_source.lower() in ["metatrader5", "mt5"]:
        data, execution_data, data_step_mode = _load_mt5_data(
            request, user_id, resolution, need_high_res, data_step_mode
        )
    else:
        data, execution_data, data_step_mode = _load_dukascopy_data(
            request, need_high_res, data_step_mode
        )

    if data is None or data.empty:
        raise ValueError(
            f"Failed to load data from {data_source} for {request.symbol} "
            f"{request.timeframe}"
        )

    return data, execution_data, data_step_mode, data_source


def _build_engine(
    engine_type: str,
    strategy_instance,
    data,
    execution_data,
    data_step_mode: str,
    request: BacktestRequest,
    slippage_config: Dict[str, Any],
    spread_config: Dict[str, Any],
    position_sizer: Optional[PositionSizer] = None,
):
    if engine_type == "vectorized":
        return VectorizedEngine(
            strategy=strategy_instance,
            data=data,
            initial_balance=request.initial_capital,
            commission=request.commission,
            slippage_points=request.slippage,
            slippage_config=slippage_config,
            spread_config=spread_config,
            leverage=request.leverage,
            timeframe=request.timeframe,
            position_sizer=position_sizer,
        )

    return EventDrivenEngine(
        strategy=strategy_instance,
        data=data,
        execution_data=execution_data,
        data_step_mode=data_step_mode,
        initial_balance=request.initial_capital,
        commission=request.commission,
        slippage_points=request.slippage,
        slippage_config=slippage_config,
        spread_config=spread_config,
        leverage=request.leverage,
        timeframe=request.timeframe,
        position_sizer=position_sizer,
    )


def _run_portfolio_backtest(
    backtest_id: int,
    user_id: int,
    strategy_class: Any,
    version: Dict[str, Any],
    request: BacktestRequest,
) -> None:
    """Run a multi-symbol portfolio backtest."""
    symbols = _parse_symbols(request.symbol)
    logger.info(f"Starting portfolio backtest with {len(symbols)} symbols: {symbols}")

    # Load data for all symbols
    datasets = _load_portfolio_data(symbols, request, user_id)

    if len(datasets) == 0:
        raise ValueError("No data loaded for any symbol in portfolio")

    if len(datasets) < len(symbols):
        missing = set(symbols) - set(datasets.keys())
        logger.warning(f"Could not load data for symbols: {missing}")

    # Get strategy parameters
    params = dict(version.get("parameters") or {})

    # Build asset specifications and strategies for each symbol
    asset_specs = {}
    strategies = {}

    for symbol in datasets.keys():
        # Create asset spec
        asset_specs[symbol] = _create_asset_spec(symbol, request)

        # Create strategy instance with symbol-specific params
        symbol_params = params.copy()
        symbol_params["symbol"] = symbol
        symbol_params["timeframe"] = request.timeframe

        strategy_instance = strategy_class(params=symbol_params)
        strategy_instance.symbol = symbol
        strategies[symbol] = strategy_instance

    # Create portfolio strategy
    portfolio_strategy = PortfolioStrategy(
        name=f"Portfolio Backtest {backtest_id}",
        strategies=strategies,
        asset_specs=asset_specs,
        data=datasets,
        max_total_exposure=1.0,
        max_correlated_exposure=0.6,
        rebalance_frequency="monthly",
    )

    # Build position sizer for portfolio
    position_sizer = _build_position_sizer(request)

    # Create and run portfolio engine
    portfolio_engine = PortfolioEngine(
        portfolio_strategy=portfolio_strategy,
        initial_balance=request.initial_capital,
        engines={},
        config={
            "commission": request.commission,
            "timeframe": request.timeframe,
            "slippage_points": request.slippage,
        },
        position_sizer=position_sizer,
    )

    portfolio_result = portfolio_engine.run()

    # Convert portfolio result to standard BacktestResult for persistence
    # We aggregate the results from all assets
    from apps.backtest.result import BacktestResult

    # Combine all trades from portfolio
    all_trades = portfolio_result.all_trades

    # Create aggregated result
    # BacktestResult is a dataclass - only pass valid constructor args
    # Properties like total_return, win_rate are computed automatically
    first_data = next(iter(datasets.values()))
    start_date = first_data.index[0].to_pydatetime()
    end_date = first_data.index[-1].to_pydatetime()

    aggregated_result = BacktestResult(
        strategy_name=portfolio_strategy.name,
        symbol=", ".join(datasets.keys()),
        timeframe=request.timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_balance=portfolio_result.initial_balance,
        backtest_mode="portfolio",
        data_step_mode="trading_timeframe",
        final_balance=portfolio_result.final_balance,
        final_equity=portfolio_result.final_equity,
        trades=all_trades,
        equity_curve=portfolio_result.equity_curve,
        metadata={"symbols": list(datasets.keys()), "engine_type": "portfolio"},
    )

    # Save results
    backtest_db.save_result(aggregated_result, backtest_id=backtest_id)

    logger.info(
        f"Portfolio backtest {backtest_id} completed: "
        f"Final balance ${portfolio_result.final_balance:.2f}, "
        f"{len(all_trades)} total trades across {len(datasets)} symbols"
    )


def _build_backtest_response(
    backtest: Dict[str, Any], metrics: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    # Handle multiple symbols (portfolio backtest)
    symbols = backtest.get("symbols", [])
    symbol_str = ", ".join(symbols) if symbols else None

    return {
        "backtest_id": backtest["backtest_id"],
        "strategy_version_id": backtest.get("strategy_version_id"),
        "status": backtest["status"],
        "strategy_name": backtest["strategy_name"],
        "symbol": symbol_str,
        "timeframe": (
            backtest.get("timeframes", [""])[0] if backtest.get("timeframes") else None
        ),
        "start_date": backtest.get("start_date"),
        "end_date": backtest.get("end_date"),
        "initial_balance": backtest.get("initial_balance"),
        "final_balance": backtest.get("final_balance"),
        "total_trades": (
            metrics.get("trade_metrics", {}).get("total_trades") if metrics else None
        ),
        "win_rate": (
            metrics.get("trade_metrics", {}).get("win_rate") if metrics else None
        ),
        "profit_factor": (
            metrics.get("trade_metrics", {}).get("profit_factor") if metrics else None
        ),
        "sharpe_ratio": (
            metrics.get("ratio_metrics", {}).get("sharpe") if metrics else None
        ),
        "max_drawdown": (
            metrics.get("drawdown_metrics", {}).get("max_drawdown") if metrics else None
        ),
        "created_at": backtest["created_at"],
        "completed_at": backtest.get("completed_at"),
        "alias": backtest.get("alias"),
        "description": backtest.get("description"),
        "engine_type": backtest.get("engine_type"),
        "data_resolution": backtest.get("data_resolution"),
    }


def _get_backtest_metrics(backtest_id: int, status: str):
    if status != "completed":
        return None

    metrics = None
    with suppress(Exception):
        metrics = db_manager.get_backtest_finance_metrics(backtest_id)
    return metrics


def _update_backtest_metadata(
    backtest_id: int, request: "BacktestUpdateRequest"
) -> None:
    import sqlite3

    conn = sqlite3.connect(db_manager.db_path)
    try:
        cursor = conn.cursor()
        update_fields: List[str] = []
        values: List[object] = []

        if request.alias is not None:
            update_fields.append("alias = ?")
            values.append(request.alias)

        if request.description is not None:
            update_fields.append("description = ?")
            values.append(request.description)

        if update_fields:
            values.append(backtest_id)
            query = (
                f"UPDATE backtest_runs SET {', '.join(update_fields)} "
                "WHERE backtest_id = ?"
            )
            cursor.execute(query, values)
            conn.commit()
            logger.info(f"Backtest {backtest_id} updated successfully")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _load_strategy_class(
    user_id: int, strategy_id: int, version_id: int
) -> tuple[Dict[str, Any], Any]:
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

    return version, strategy_class


async def _run_backtest_task(
    backtest_id: int,
    user_id: int,
    strategy_id: int,
    version_id: int,
    request: BacktestRequest,
) -> None:
    """Background task to run a backtest."""
    # Get the current event loop for scheduling coroutines
    loop = asyncio.get_event_loop()

    # Setup WebSocket log streaming with callable sink
    def log_sink(record: Any) -> None:
        """Callable sink for WebSocket log streaming.

        Args:
            record: LogRecord object from the logger
        """
        # Always buffer logs - they'll be sent when WebSocket connects
        # Extract log data from the LogRecord object
        log_data = {
            "timestamp": record.time.isoformat(),
            "level": record.level.name,
            "message": record.message,
            "source": record.name,
            "backtest_id": backtest_id,
        }
        # Use run_coroutine_threadsafe to schedule the coroutine on the event loop.
        # This is necessary because log_sink is called from a synchronous context.
        with suppress(Exception):
            asyncio.run_coroutine_threadsafe(
                backtest_log_manager.broadcast(backtest_id, log_data), loop
            )

    # Add WebSocket handler with raw=True to receive LogRecord objects directly
    handler_id = logger.add(log_sink, level="INFO", raw=True)

    try:
        # Wait for frontend to establish WebSocket connection for real-time logs
        # This delay allows the frontend to receive the backtest_id response,
        # mount the ExecutionView, and connect via WebSocket before logs start
        await asyncio.sleep(2.0)

        # Update status to running
        db_manager.update_backtest_status(backtest_id, "running")

        # Check if this is a portfolio backtest (multiple symbols)
        is_portfolio = _is_portfolio_backtest(request.symbol)

        if is_portfolio:
            symbols = _parse_symbols(request.symbol)
            logger.info(
                f"Running PORTFOLIO backtest {backtest_id} with {len(symbols)} symbols: "
                f"{', '.join(symbols)}"
            )

            version, strategy_class = _load_strategy_class(
                user_id=user_id, strategy_id=strategy_id, version_id=version_id
            )

            # Run portfolio backtest
            _run_portfolio_backtest(
                backtest_id=backtest_id,
                user_id=user_id,
                strategy_class=strategy_class,
                version=version,
                request=request,
            )

            logger.info(f"Portfolio backtest {backtest_id} completed successfully")
        else:
            # Single-symbol backtest (original flow)
            logger.info(f"Running backtest {backtest_id} for {request.symbol}...")

            version, strategy_class = _load_strategy_class(
                user_id=user_id, strategy_id=strategy_id, version_id=version_id
            )
            data, execution_data, data_step_mode, _ = _load_backtest_data(
                request, user_id
            )

            logger.info(f"Total Signal Bars: {len(data)}")

            # Run backtest
            params = dict(version.get("parameters") or {})

            # Add symbol and timeframe to params for strategy initialization
            params["symbol"] = request.symbol
            params["timeframe"] = request.timeframe

            # Instantiate strategy with parameters dict
            # Strategy expects params as a single dict argument, not as **kwargs
            strategy_instance = strategy_class(params=params)

            # Set symbol on strategy instance for engine access
            strategy_instance.symbol = request.symbol

            # Select engine based on engine type
            engine_type = request.engine_type or "event-driven"

            # Prepare slippage config
            slippage_config = {
                "type": request.slippage_type or "fixed",
                "fixed": request.slippage,
                "min": request.slippage_min,
                "max": request.slippage_max,
            }

            # Prepare spread config
            spread_config = {
                "type": request.spread_type or "use-broker",
                "fixed": request.spread,
                "min": request.spread_min,
                "max": request.spread_max,
            }

            # Build position sizer
            position_sizer = _build_position_sizer(request)

            engine = _build_engine(
                engine_type=engine_type,
                strategy_instance=strategy_instance,
                data=data,
                execution_data=execution_data,
                data_step_mode=data_step_mode,
                request=request,
                slippage_config=slippage_config,
                spread_config=spread_config,
                position_sizer=position_sizer,
            )

            results = engine.run()

            # Save results using BacktestDatabase (wraps 4-layer architecture)
            backtest_db.save_result(results, backtest_id=backtest_id)

            logger.info(
                f"Backtest {backtest_id} completed successfully and saved to database"
            )

    except Exception as e:
        logger.error(f"Backtest {backtest_id} failed: {e}")
        db_manager.update_backtest_status(backtest_id, "failed")
    finally:
        # Remove WebSocket log handler
        try:
            logger.remove(handler_id)
            logger.info(f"WebSocket handler removed for backtest {backtest_id}")
        except Exception as e:
            logger.warning(f"Error removing WebSocket handler: {e}")

        # Clear log buffer to free memory
        # Wait long enough for frontend to establish WebSocket and receive buffered logs
        try:
            await asyncio.sleep(5.0)  # 5 seconds to allow late WebSocket connections
            await backtest_log_manager.clear_buffer(backtest_id)
            logger.info(f"Log buffer cleared for backtest {backtest_id}")
        except Exception as e:
            logger.warning(f"Error clearing log buffer: {e}")

        logger.info(f"Background task completed for backtest {backtest_id}")


# --- Endpoints ---


@router.post("/run/{strategy_id}", response_model=BacktestResponse)
async def run_backtest(
    strategy_id: int,
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    authorization: Annotated[Optional[str], Header()] = None,
) -> BacktestResponse:
    """
    Run a backtest for a strategy.

    Executes asynchronously in the background.
    """
    try:
        user_id = get_user_id_from_token(authorization)
        # Get strategy and active version
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy or not strategy["active_version_id"]:
            logger.warning(f"Strategy {strategy_id} or active version not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} or active version not found",
            )

        version_id = strategy["active_version_id"]

        # Parse symbols (single or comma-separated for portfolio)
        symbols = _parse_symbols(request.symbol)
        is_portfolio = len(symbols) > 1

        # Create backtest run using new 4-layer system
        start_dt = _parse_request_date(request.start_date) or datetime.now()
        end_dt = _parse_request_date(request.end_date) or datetime.now()

        # For portfolio backtests, update engine type to portfolio
        engine_type = request.engine_type or "event-driven"
        if is_portfolio:
            engine_type = "portfolio"

        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",  # You can enhance this to get actual version
            start_date=start_dt,
            end_date=end_dt,
            engine_type=engine_type,
            data_resolution=request.data_resolution or "timeframe",
            config_hash=str(hash((strategy_id, request.symbol, request.timeframe))),
            symbols=symbols,
            timeframes=[request.timeframe],
            initial_balance=request.initial_capital,
            alias=request.alias,
            description=request.description,
            strategy_version_id=version_id,
            user_id=user_id,
        )

        # Run backtest in background
        background_tasks.add_task(
            _run_backtest_task,
            backtest_id=backtest_id,
            user_id=user_id,
            strategy_id=strategy_id,
            version_id=version_id,
            request=request,
        )

        # Get backtest record
        backtest_run = db_manager.get_backtest_run(backtest_id)
        if backtest_run is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load backtest run",
            )

        if is_portfolio:
            logger.info(
                f"Portfolio backtest {backtest_id} started for strategy {strategy_id} "
                f"with {len(symbols)} symbols: {', '.join(symbols)}"
            )
        else:
            logger.info(f"Backtest {backtest_id} started for strategy {strategy_id}")

        # Convert to response format
        # For portfolio backtests, symbol field contains comma-separated symbols
        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "strategy_version_id": backtest_run.get("strategy_version_id"),
            "status": backtest_run["status"],
            "strategy_name": backtest_run["strategy_name"],
            "symbol": ", ".join(symbols) if is_portfolio else symbols[0],
            "timeframe": request.timeframe,
            "start_date": backtest_run["start_date"],
            "end_date": backtest_run["end_date"],
            "initial_balance": backtest_run["initial_balance"],
            "final_balance": backtest_run.get("final_balance"),
            "total_trades": None,
            "win_rate": None,
            "profit_factor": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "created_at": backtest_run["created_at"],
            "completed_at": backtest_run.get("completed_at"),
            "engine_type": engine_type,
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start backtest: {str(e)}",
        )


@router.get("/strategy/{strategy_id}", response_model=List[BacktestResponse])
async def list_strategy_backtests(strategy_id: int) -> List[BacktestResponse]:
    """List all backtests for a strategy."""
    try:
        # Get active version
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy or not strategy["active_version_id"]:
            return []

        # Get all backtests using new system
        backtests = db_manager.get_all_backtests(
            strategy_version_id=strategy["active_version_id"]
        )

        # Convert to response format
        response_list = []
        for bt in backtests:
            # Get finance metrics if completed
            metrics = None
            if bt["status"] == "completed":
                with suppress(Exception):
                    metrics = db_manager.get_backtest_finance_metrics(bt["backtest_id"])

            # Handle multiple symbols (portfolio backtest)
            bt_symbols = bt.get("symbols", [])
            response_data = {
                "backtest_id": bt["backtest_id"],
                "strategy_id": strategy_id,
                "strategy_version_id": bt.get("strategy_version_id"),
                "status": bt["status"],
                "strategy_name": bt["strategy_name"],
                "symbol": ", ".join(bt_symbols) if bt_symbols else None,
                "timeframe": (
                    bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                ),
                "start_date": bt.get("start_date"),
                "end_date": bt.get("end_date"),
                "initial_balance": bt.get("initial_balance"),
                "final_balance": bt.get("final_balance"),
                "total_trades": (
                    metrics.get("trade_metrics", {}).get("total_trades")
                    if metrics
                    else None
                ),
                "win_rate": (
                    metrics.get("trade_metrics", {}).get("win_rate")
                    if metrics
                    else None
                ),
                "profit_factor": (
                    metrics.get("trade_metrics", {}).get("profit_factor")
                    if metrics
                    else None
                ),
                "sharpe_ratio": (
                    metrics.get("ratio_metrics", {}).get("sharpe_ratio")
                    if metrics
                    else None
                ),
                "max_drawdown": (
                    metrics.get("drawdown_metrics", {}).get("max_drawdown")
                    if metrics
                    else None
                ),
                "created_at": bt["created_at"],
                "completed_at": bt.get("completed_at"),
            }
            response_list.append(BacktestResponse(**response_data))

        return response_list

    except Exception as e:
        logger.error(f"Error listing backtests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backtests: {str(e)}",
        )


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(backtest_id: int) -> BacktestResponse:
    """Get a specific backtest."""
    try:
        # Get backtest run
        backtest = db_manager.get_backtest_run(backtest_id)

        if not backtest:
            logger.warning(f"Backtest {backtest_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        # Get finance metrics if completed
        metrics = None
        if backtest["status"] == "completed":
            with suppress(Exception):
                metrics = db_manager.get_backtest_finance_metrics(backtest_id)

        # Get trades
        trades = []
        try:
            trades = db_manager.get_backtest_trades(backtest_id)
        except Exception as e:
            logger.warning(f"Failed to fetch trades for backtest {backtest_id}: {e}")

        # Handle multiple symbols (portfolio backtest)
        backtest_symbols = backtest.get("symbols", [])
        response_data = {
            "backtest_id": backtest["backtest_id"],
            "strategy_id": backtest.get(
                "strategy_id"
            ),  # This might be None or need handling if not in raw dict
            "strategy_version_id": backtest.get("strategy_version_id"),
            "status": backtest["status"],
            "strategy_name": backtest["strategy_name"],
            "symbol": ", ".join(backtest_symbols) if backtest_symbols else None,
            "timeframe": (
                backtest.get("timeframes", [""])[0]
                if backtest.get("timeframes")
                else None
            ),
            "start_date": backtest.get("start_date"),
            "end_date": backtest.get("end_date"),
            "initial_balance": backtest.get("initial_balance"),
            "final_balance": backtest.get("final_balance"),
            "total_trades": (
                metrics.get("trade_metrics", {}).get("total_trades")
                if metrics
                else None
            ),
            "win_rate": (
                metrics.get("trade_metrics", {}).get("win_rate") if metrics else None
            ),
            "profit_factor": (
                metrics.get("trade_metrics", {}).get("profit_factor")
                if metrics
                else None
            ),
            "sharpe_ratio": (
                metrics.get("ratio_metrics", {}).get("sharpe_ratio")
                if metrics
                else None
            ),
            "max_drawdown": (
                metrics.get("drawdown_metrics", {}).get("max_drawdown")
                if metrics
                else None
            ),
            "created_at": backtest["created_at"],
            "completed_at": backtest.get("completed_at"),
            "trades": trades,
        }

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backtest: {str(e)}",
        )


@router.websocket("/ws/{backtest_id}/logs")
async def backtest_logs_websocket(websocket: WebSocket, backtest_id: int) -> None:
    """
    Websocket endpoint for streaming backtest logs in real-time.

    Clients connect to this endpoint to receive live log updates
    during backtest execution.
    """
    logger.info(f"WebSocket connection attempt for backtest {backtest_id}")

    await backtest_log_manager.connect(backtest_id, websocket)
    logger.info(f"WebSocket connected for backtest {backtest_id}")

    try:
        # Keep connection alive and listen for client messages
        while True:
            # Receive messages (ping/pong to keep connection alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Client disconnected
        logger.info(f"WebSocket disconnected for backtest {backtest_id}")
        await backtest_log_manager.disconnect(backtest_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for backtest {backtest_id}: {e}")
        await backtest_log_manager.disconnect(backtest_id, websocket)


@router.get("/", response_model=List[BacktestResponse])
async def list_all_backtests(
    user_id: int = 1, limit: int = 100
) -> List[BacktestResponse]:
    """List all backtests across all strategies."""
    try:
        # Get all backtests for the user
        backtests = db_manager.get_all_backtests(user_id=user_id, limit=limit)

        # Convert to response format
        response_list = []
        for bt in backtests:
            # Get finance metrics if completed
            metrics = None
            if bt["status"] == "completed":
                with suppress(Exception):
                    metrics = db_manager.get_backtest_finance_metrics(bt["backtest_id"])

            # Handle multiple symbols (portfolio backtest)
            all_bt_symbols = bt.get("symbols", [])
            response_data = {
                "backtest_id": bt["backtest_id"],
                "strategy_id": bt.get("strategy_id"),
                "strategy_version_id": bt.get("strategy_version_id"),
                "status": bt["status"],
                "strategy_name": bt["strategy_name"],
                "symbol": ", ".join(all_bt_symbols) if all_bt_symbols else None,
                "timeframe": (
                    bt.get("timeframes", [""])[0] if bt.get("timeframes") else None
                ),
                "start_date": bt.get("start_date"),
                "end_date": bt.get("end_date"),
                "initial_balance": bt.get("initial_balance"),
                "final_balance": bt.get("final_balance"),
                "total_trades": (
                    metrics.get("trade_metrics", {}).get("total_trades")
                    if metrics
                    else None
                ),
                "win_rate": (
                    metrics.get("trade_metrics", {}).get("win_rate")
                    if metrics
                    else None
                ),
                "profit_factor": (
                    metrics.get("trade_metrics", {}).get("profit_factor")
                    if metrics
                    else None
                ),
                "sharpe_ratio": (
                    metrics.get("ratio_metrics", {}).get("sharpe") if metrics else None
                ),
                "max_drawdown": (
                    metrics.get("drawdown_metrics", {}).get("max_drawdown")
                    if metrics
                    else None
                ),
                "created_at": bt["created_at"],
                "completed_at": bt.get("completed_at"),
                "alias": bt.get("alias"),
                "description": bt.get("description"),
                "engine_type": bt.get("engine_type"),
                "data_resolution": bt.get("data_resolution"),
            }
            response_list.append(BacktestResponse(**response_data))

        return response_list

    except Exception as e:
        logger.error(f"Error listing all backtests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list all backtests: {str(e)}",
        )


@router.put("/{backtest_id}", response_model=BacktestResponse)
async def update_backtest(
    backtest_id: int, request: BacktestUpdateRequest
) -> BacktestResponse:
    """Update backtest metadata (alias, description)."""
    try:
        # Get current backtest
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        _update_backtest_metadata(backtest_id, request)

        # Get updated backtest
        updated_backtest = db_manager.get_backtest_run(backtest_id)
        if updated_backtest is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load backtest {backtest_id}",
            )

        # Get finance metrics if completed
        metrics = _get_backtest_metrics(backtest_id, updated_backtest["status"])

        response_data = _build_backtest_response(updated_backtest, metrics)

        return BacktestResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update backtest: {str(e)}",
        )


@router.delete("/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest_endpoint(backtest_id: int) -> None:
    """Delete a backtest and all associated data (trades, metrics, etc.)."""
    try:
        # Check if backtest exists
        backtest = db_manager.get_backtest_run(backtest_id)
        if not backtest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_id} not found",
            )

        # Delete backtest (cascades to all related tables)
        success = db_manager.delete_backtest(backtest_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete backtest {backtest_id}",
            )

        logger.info(
            f"Backtest {backtest_id} deleted successfully with all associated data"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backtest: {str(e)}",
        )
