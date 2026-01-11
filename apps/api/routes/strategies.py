"""Strategy routes for managing trading strategies."""

import asyncio
import os
import tempfile
from contextlib import suppress
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from apps.api.websocket import backtest_log_manager
from apps.backtest import EventDrivenEngine, VectorizedEngine
from apps.backtest.persistence import BacktestDatabase
from apps.logger import logger
from apps.sqlite.database_operations import DatabaseManager
from apps.strategy import storage
from apps.utils.data_getters import load_dukascopy

router = APIRouter()
db_manager = DatabaseManager()
backtest_db = BacktestDatabase()
IMPORT_FILE = File(...)


# Pydantic models for request/response
class StrategyCreateRequest(BaseModel):
    """Request payload for creating a strategy."""

    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    code: str
    parameters: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    type: Optional[str] = None
    moneyManagement: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None


class StrategyUpdateRequest(BaseModel):
    """Request payload for updating a strategy."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    type: Optional[str] = None
    moneyManagement: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None


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
    alias: Optional[str] = None
    description: Optional[str] = None


class StrategyResponse(BaseModel):
    """Response model for strategy metadata."""

    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: str
    category: Optional[str]
    is_public: bool
    active_version: Optional[str]
    active_version_id: Optional[int]
    created_at: str
    updated_at: str


class VersionResponse(BaseModel):
    """Response model for strategy versions."""

    id: int
    strategy_id: int
    version: str
    parameters: Dict[str, Any]
    changelog: Optional[str]
    created_at: str


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


class PerformanceSummaryRequest(BaseModel):
    """Request payload for summarizing performance."""

    trades: List[Dict[str, Any]]
    initial_balance: float = 10000.0


def _build_strategy_update_fields(request: StrategyUpdateRequest) -> Dict[str, Any]:
    update_fields: Dict[str, Any] = {}
    if request.name:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.status:
        update_fields["status"] = request.status
    if request.category:
        update_fields["category"] = request.category
    return update_fields


def _next_strategy_version(db_versions: List[Dict[str, Any]]) -> str:
    if not db_versions:
        return "1.0.0"

    last_version = db_versions[0]["version"]
    major, minor, patch = map(int, last_version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def _create_strategy_version(
    strategy_id: int,
    request: StrategyUpdateRequest,
    user_id: int,
    username: str,
    strategy_name: str,
):
    db_versions = db_manager.get_strategy_versions(strategy_id)
    new_version = _next_strategy_version(db_versions)

    file_path = storage.save_strategy(
        user_id=user_id,
        strategy_id=strategy_id,
        version=new_version,
        code=request.code or "",
        parameters=request.parameters or {},
        username=username,
        strategy_name=strategy_name,
        metadata={
            "name": request.name or strategy_name,
            "description": request.description,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "type": request.type,
            "moneyManagement": request.moneyManagement,
            "variables": request.variables,
            "changelog": request.changelog or f"Updated to v{new_version}",
        },
    )

    db_manager.create_strategy_version(
        strategy_id=strategy_id,
        version=new_version,
        file_path=file_path,
        parameters=request.parameters,
        changelog=request.changelog,
        created_by=user_id,
    )

    return new_version


def _load_strategy_class(
    user_id: int, strategy_id: int, version_id: int
) -> tuple[Dict[str, Any], Any]:
    version = db_manager.get_strategy_version(version_id)
    strategy = db_manager.get_strategy(strategy_id)
    user = db_manager.get_user(user_id=user_id)
    username = user.get("username") if user else ""
    strategy_name = strategy.get("name") if strategy else ""

    strategy_class = storage.load_strategy_class(
        user_id=user_id,
        strategy_id=strategy_id,
        version=version["version"],
        username=username,
        strategy_name=strategy_name,
    )

    return version, strategy_class


def _resolve_resolution(request: BacktestRequest) -> tuple[str, str, bool]:
    resolution = (request.data_resolution or "timeframe").lower()
    data_step_mode = "trading_timeframe"
    if resolution == "m1":
        data_step_mode = "m1_bars"
    elif resolution == "tick":
        data_step_mode = "tick"

    need_high_res = resolution in ["m1", "tick"]
    return resolution, data_step_mode, need_high_res


def _fetch_mt5_signal_data(mt5_data, request, tf_enum):
    logger.info(f"Fetching Signal Data ({request.timeframe})...")
    if request.range_by == "bars":
        logger.info(f"Loading {request.number_of_bars} bars")
        data = mt5_data.get_bars(
            symbol=request.symbol,
            timeframe=tf_enum,
            count=request.number_of_bars,
        )
    else:
        data = mt5_data.get_bars(
            symbol=request.symbol,
            timeframe=tf_enum,
            start=request.start_date,
            end=request.end_date,
        )
    return data


def _fetch_mt5_execution_data(
    mt5_data, request, time_frame_enum, mt5_module, resolution
):
    if resolution == "m1":
        if request.range_by == "bars":
            tf_minutes = time_frame_enum.from_string(request.timeframe).minutes
            m1_count = request.number_of_bars * tf_minutes
            return mt5_data.get_bars(
                symbol=request.symbol,
                timeframe=time_frame_enum.M1,
                count=m1_count,
            )
        return mt5_data.get_bars(
            symbol=request.symbol,
            timeframe=time_frame_enum.M1,
            start=request.start_date,
            end=request.end_date,
        )

    if resolution == "tick":
        if request.range_by == "bars":
            tick_count = request.number_of_bars * 100
            return mt5_data.get_ticks(
                symbol=request.symbol,
                count=tick_count,
                flags=mt5_module.COPY_TICKS_ALL,
            )
        return mt5_data.get_ticks(
            symbol=request.symbol,
            start=request.start_date,
            end=request.end_date,
            flags=mt5_module.COPY_TICKS_ALL,
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
    import MetaTrader5 as mt5

    from apps.mt5.client import MT5Client
    from apps.mt5.data import MT5Data, TimeFrame

    client = MT5Client()
    if not client.initialize():
        raise RuntimeError("Failed to connect to MT5")

    mt5_data = MT5Data(client=client)
    data = None
    execution_data = None

    try:
        tf_enum = TimeFrame.from_string(request.timeframe)
        data = _fetch_mt5_signal_data(mt5_data, request, tf_enum)

        if data is None or data.empty:
            raise ValueError(f"No {request.timeframe} data found for {request.symbol}")

        from apps.utils.data_validator import DataValidator

        data = DataValidator.prepare_data(data)

        if need_high_res:
            logger.info(f"Fetching Execution Data ({resolution})...")
            execution_data = _fetch_mt5_execution_data(
                mt5_data, request, TimeFrame, mt5, resolution
            )
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
    )


def _build_backtest_response(
    backtest: Dict[str, Any], metrics: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "backtest_id": backtest["backtest_id"],
        "strategy_version_id": backtest.get("strategy_version_id"),
        "status": backtest["status"],
        "strategy_name": backtest["strategy_name"],
        "symbol": (
            backtest.get("symbols", [""])[0] if backtest.get("symbols") else None
        ),
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


# Template endpoints
@router.get("/templates/{template_name}")
async def get_strategy_template(template_name: str) -> Dict[str, str]:
    """
    Get a strategy template by name.

    Available templates:
    - empty: Empty strategy template with TODO comments
    - trend_following: EMA crossover trend following strategy
    """
    try:
        # Map template names to files
        template_map = {
            "empty": "template_strategy.py",
            "trend_following": "../../examples/strategy/trend_following.py",
        }

        if template_name not in template_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found. Available: {list(template_map.keys())}",
            )

        # Get template file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        template_file = os.path.join(
            project_root, "apps", "strategy", "templates", template_map[template_name]
        )

        # Read template content
        if not os.path.exists(template_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template file not found: {template_file}",
            )

        with open(template_file, "r", encoding="utf-8") as f:
            code = f.read()

        logger.info(f"Serving template: {template_name}")

        return {
            "template_name": template_name,
            "code": code,
            "description": f"{template_name.replace('_', ' ').title()} Strategy Template",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template '{template_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load template: {str(e)}",
        )


# Strategy CRUD endpoints
@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: StrategyCreateRequest, user_id: int = 1
) -> StrategyResponse:
    """
    Create a new strategy.

    Note: In production, user_id would come from authentication token.
    For now, defaulting to user_id=1 for testing.
    """
    try:
        logger.info(f"Creating strategy: {request.name} for user {user_id}")

        # Create strategy in database
        strategy_id = db_manager.create_strategy(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category,
            status="inactive",
            is_public=False,
        )

        # Get username for descriptive folder naming
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Save strategy code to file (version 1.0.0)
        version = "1.0.0"
        file_path = storage.save_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            code=request.code,
            parameters=request.parameters,
            username=username,
            strategy_name=request.name,
            metadata={
                "name": request.name,
                "description": request.description,
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "type": request.type,
                "moneyManagement": request.moneyManagement,
                "variables": request.variables,
            },
        )

        # Create version record
        _ = db_manager.create_strategy_version(
            strategy_id=strategy_id,
            version=version,
            file_path=file_path,
            parameters=request.parameters,
            changelog="Initial version",
            created_by=user_id,
        )

        # Get created strategy
        strategy = db_manager.get_strategy(strategy_id)

        logger.info(f"Strategy created successfully: ID={strategy_id}")

        return StrategyResponse(**strategy)

    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}",
        )


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(
    user_id: int = 1,
    strategy_status: Optional[str] = None,
    category: Optional[str] = None,
    include_shared: bool = False,
) -> List[StrategyResponse]:
    """List all strategies for a user."""
    try:
        strategies = db_manager.get_user_strategies(
            user_id=user_id,
            status=strategy_status,
            category=category,
            include_shared=include_shared,
        )

        return [StrategyResponse(**s) for s in strategies]

    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list strategies: {str(e)}",
        )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int) -> StrategyResponse:
    """Get a specific strategy."""
    try:
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        return StrategyResponse(**strategy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy: {str(e)}",
        )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int, request: StrategyUpdateRequest, user_id: int = 1
) -> StrategyResponse:
    """
    Update a strategy.

    If code is provided, creates a new version.
    """
    try:
        # Get current strategy
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        update_fields = _build_strategy_update_fields(request)
        if update_fields:
            db_manager.update_strategy(strategy_id, **update_fields)

        if request.code:
            user = db_manager.get_user(user_id=user_id)
            username = user.get("username", "") if user else ""
            strategy_name = request.name or strategy["name"]
            new_version = _create_strategy_version(
                strategy_id=strategy_id,
                request=request,
                user_id=user_id,
                username=username,
                strategy_name=strategy_name,
            )
            logger.info(
                f"New version created: {new_version} for strategy {strategy_id}"
            )

        # Get updated strategy
        updated_strategy = db_manager.get_strategy(strategy_id)

        return StrategyResponse(**updated_strategy)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}",
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: int, user_id: int = 1) -> None:
    """Delete a strategy and all its versions."""
    try:
        # Get strategy info before deleting from database
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy:
            logger.warning(f"Strategy {strategy_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )

        # Get username for folder path
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""
        strategy_name = strategy.get("name", "") if strategy else ""

        # Delete from database
        success = db_manager.delete_strategy(strategy_id)

        if not success:
            logger.warning(f"Failed to delete strategy {strategy_id} from database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete strategy {strategy_id}",
            )

        # Delete files with username and strategy name for new folder structure
        storage.delete_strategy(
            user_id, strategy_id, username=username, strategy_name=strategy_name
        )

        logger.info(f"Strategy {strategy_id} deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete strategy: {str(e)}",
        )


# Version endpoints
@router.get("/{strategy_id}/versions", response_model=List[VersionResponse])
async def list_versions(strategy_id: int) -> List[VersionResponse]:
    """List all versions of a strategy."""
    try:
        versions = db_manager.get_strategy_versions(strategy_id)
        return [VersionResponse(**v) for v in versions]

    except Exception as e:
        logger.error(f"Error listing versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list versions: {str(e)}",
        )


@router.get("/{strategy_id}/versions/{version_id}/code")
async def get_version_code(
    strategy_id: int, version_id: int, user_id: int = 1
) -> Dict[str, Any]:
    """Get the code for a specific version."""
    try:
        # Get version info
        version = db_manager.get_strategy_version(version_id)

        if not version:
            logger.warning(f"Version {version_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version_id} not found",
            )

        # Get strategy info for name
        strategy = db_manager.get_strategy(strategy_id)
        strategy_name = strategy.get("name", "") if strategy else ""

        # Get user info for username
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Load code and metadata from file
        code = storage.load_strategy_code(
            user_id, strategy_id, version["version"], username, strategy_name
        )
        metadata = storage.load_strategy_metadata(
            user_id, strategy_id, version["version"], username, strategy_name
        )

        return {
            "version_id": version_id,
            "version": version["version"],
            "code": code,
            "parameters": version["parameters"],
            "symbol": metadata.get("symbol"),
            "timeframe": metadata.get("timeframe"),
            "type": metadata.get("type"),
            "moneyManagement": metadata.get("moneyManagement"),
            "variables": metadata.get("variables"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get version code: {str(e)}",
        )


@router.post("/{strategy_id}/versions/{version_id}/rollback")
async def rollback_version(strategy_id: int, version_id: int) -> Dict[str, str]:
    """Rollback to a specific version (make it the active version)."""
    try:
        # Update strategy's active version
        db_manager.update_strategy(strategy_id, active_version_id=version_id)

        logger.info(f"Strategy {strategy_id} rolled back to version {version_id}")

        return {"message": "Version rolled back successfully"}

    except Exception as e:
        logger.error(f"Error rolling back version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback version: {str(e)}",
        )


# Backtest endpoints
@router.post("/{strategy_id}/backtest", response_model=BacktestResponse)
async def run_backtest(
    strategy_id: int,
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    user_id: int = 1,
) -> BacktestResponse:
    """
    Run a backtest for a strategy.

    Executes asynchronously in the background.
    """
    try:
        # Get strategy and active version
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy or not strategy["active_version_id"]:
            logger.warning(f"Strategy {strategy_id} or active version not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} or active version not found",
            )

        version_id = strategy["active_version_id"]

        # Create backtest run using new 4-layer system
        backtest_id = db_manager.create_backtest_run(
            strategy_name=strategy["name"],
            strategy_version="1.0.0",  # You can enhance this to get actual version
            start_date=request.start_date or "N/A",
            end_date=request.end_date or "N/A",
            engine_type=request.engine_type or "event-driven",
            data_resolution=request.data_resolution or "timeframe",
            config_hash=str(hash((strategy_id, request.symbol, request.timeframe))),
            symbols=[request.symbol],
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

        logger.info(f"Backtest {backtest_id} started for strategy {strategy_id}")

        # Convert to response format
        response_data = {
            "backtest_id": backtest_run["backtest_id"],
            "strategy_version_id": backtest_run.get("strategy_version_id"),
            "status": backtest_run["status"],
            "strategy_name": backtest_run["strategy_name"],
            "symbol": request.symbol,
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

        logger.info(f"Running backtest {backtest_id}...")

        # Update status to running
        db_manager.update_backtest_status(backtest_id, "running")

        version, strategy_class = _load_strategy_class(
            user_id=user_id, strategy_id=strategy_id, version_id=version_id
        )
        data, execution_data, data_step_mode, _ = _load_backtest_data(request, user_id)

        logger.info(f"Total Signal Bars: {len(data)}")

        # Run backtest
        params = version.get("parameters", {})

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

        engine = _build_engine(
            engine_type=engine_type,
            strategy_instance=strategy_instance,
            data=data,
            execution_data=execution_data,
            data_step_mode=data_step_mode,
            request=request,
            slippage_config=slippage_config,
            spread_config=spread_config,
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


@router.get("/{strategy_id}/backtests", response_model=List[BacktestResponse])
async def list_backtests(strategy_id: int) -> List[BacktestResponse]:
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

            response_data = {
                "backtest_id": bt["backtest_id"],
                "strategy_id": strategy_id,
                "strategy_version_id": bt.get("strategy_version_id"),
                "status": bt["status"],
                "strategy_name": bt["strategy_name"],
                "symbol": bt.get("symbols", [""])[0] if bt.get("symbols") else None,
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


@router.get("/{strategy_id}/backtests/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(strategy_id: int, backtest_id: int) -> BacktestResponse:
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

        response_data = {
            "backtest_id": backtest["backtest_id"],
            "strategy_id": strategy_id,
            "strategy_version_id": backtest.get("strategy_version_id"),
            "status": backtest["status"],
            "strategy_name": backtest["strategy_name"],
            "symbol": (
                backtest.get("symbols", [""])[0] if backtest.get("symbols") else None
            ),
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


@router.websocket("/ws/backtest/{backtest_id}/logs")
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


# Backtest update request model
class BacktestUpdateRequest(BaseModel):
    """Request payload for updating backtest metadata."""

    alias: Optional[str] = None
    description: Optional[str] = None


# All backtests endpoint (not filtered by strategy)
@router.get("/backtests/all", response_model=List[BacktestResponse])
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

            response_data = {
                "backtest_id": bt["backtest_id"],
                "strategy_id": bt.get("strategy_id"),
                "strategy_version_id": bt.get("strategy_version_id"),
                "status": bt["status"],
                "strategy_name": bt["strategy_name"],
                "symbol": bt.get("symbols", [""])[0] if bt.get("symbols") else None,
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


@router.put("/backtests/{backtest_id}", response_model=BacktestResponse)
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


@router.delete("/backtests/{backtest_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.get("/backtests/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_by_id(backtest_id: int) -> BacktestResponse:
    """Get a specific backtest by ID (without needing strategy_id)."""
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

        response_data = {
            "backtest_id": backtest["backtest_id"],
            "strategy_id": backtest.get(
                "strategy_id"
            ),  # Now available via previous join fix if query used join vs direct get. db_manager.get_backtest_run uses direct select so we might miss it but strategy_id is not critical for this specific request, backtest_id is primary. Actually get_backtest_run is simple select.
            "strategy_version_id": backtest.get("strategy_version_id"),
            "status": backtest["status"],
            "strategy_name": backtest["strategy_name"],
            "symbol": (
                backtest.get("symbols", [""])[0] if backtest.get("symbols") else None
            ),
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
            "alias": backtest.get("alias"),
            "description": backtest.get("description"),
            "engine_type": backtest.get("engine_type"),
            "data_resolution": backtest.get("data_resolution"),
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


# Export/Import endpoints
@router.post("/{strategy_id}/export")
async def export_strategy(strategy_id: int, user_id: int = 1) -> FileResponse:
    """Export strategy as a zip file."""
    try:
        strategy = db_manager.get_strategy(strategy_id)

        if not strategy or not strategy["active_version"]:
            logger.warning(f"Strategy {strategy_id} or active version not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} or active version not found",
            )

        # Create temp file for export
        temp_dir = tempfile.gettempdir()
        export_path = os.path.join(
            temp_dir, f"strategy_{strategy_id}_v{strategy['active_version']}.zip"
        )
        logger.debug(
            f"Exporting strategy {strategy_id} v{strategy['active_version']} to {export_path}"
        )

        # Get username for folder path
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Export strategy
        zip_path = storage.export_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=strategy["active_version"],
            export_path=export_path,
            username=username,
            strategy_name=strategy["name"],
        )

        return FileResponse(
            zip_path, media_type="application/zip", filename=os.path.basename(zip_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export strategy: {str(e)}",
        )


@router.post("/{strategy_id}/import")
async def import_strategy(
    strategy_id: int, file: UploadFile = IMPORT_FILE, user_id: int = 1
) -> Dict[str, str]:
    """Import strategy from a zip file."""
    try:
        # Save uploaded file to temp location
        temp_dir = tempfile.gettempdir()
        import_path = os.path.join(temp_dir, file.filename or "unknown.zip")

        with open(import_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Get strategy info for name
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found",
            )
        strategy_name = strategy.get("name", "")

        # Get user info for username
        user = db_manager.get_user(user_id=user_id)
        username = user.get("username", "") if user else ""

        # Determine next version
        versions = storage.list_versions(username=username, strategy_name=strategy_name)

        if versions:
            last_version = versions[0]
            major = int(last_version.split(".")[0])
            new_version = f"{major + 1}.0.0"  # Major version bump for imports
            logger.debug(
                f"Importing as new version {new_version} (previous: {last_version})"
            )
        else:
            new_version = "1.0.0"
            logger.debug(f"Importing as initial version {new_version}")

        # Import strategy
        file_path = storage.import_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            version=new_version,
            import_path=import_path,
            username=username,
            strategy_name=strategy_name,
        )

        # Load metadata if exists
        metadata = storage.load_strategy_metadata(
            user_id,
            strategy_id,
            new_version,
            username=username,
            strategy_name=strategy_name,
        )

        # Create version record
        db_manager.create_strategy_version(
            strategy_id=strategy_id,
            version=new_version,
            file_path=file_path,
            parameters=metadata.get("parameters", {}),
            changelog=f"Imported from {file.filename}",
            created_by=user_id,
        )
        logger.info(f"Strategy version created from import: {file.filename}")

        # Clean up temp file
        os.remove(import_path)

        logger.info(f"Strategy imported: version {new_version}")

        return {"message": "Strategy imported successfully", "version": new_version}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import strategy: {str(e)}",
        )
