"""Optimization API routes."""

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from apps.api.websocket import optimization_progress_manager
from apps.utils.logger import logger
from apps.optimization.models import (
    ConsecutiveLosingRequest,
    ConsecutiveLosingResponse,
    ConsecutiveLosingScenario,
    MonteCarloRequest,
    MonteCarloResponse,
    MultiEntryRequest,
    MultiEntryResponse,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationResultItem,
    OptimizationRunDetails,
    ParametricMonteCarloRequest,
    PositionSizingRequest,
    ProfitTargetRequest,
    ProfitTargetResponse,
    ProfitTargetResult,
    RandomWinRateRequest,
    RandomWinRateResponse,
    RobustnessRequest,
    RobustnessResponse,
    WalkForwardRequest,
)
from apps.optimization.monte_carlo import (
    ParametricSimulationResult,
    consecutive_losing_simulation,
    parametric_simulation,
    position_sizing_simulation,
    profit_target_simulation,
    random_win_rate_simulation,
)
from apps.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()


def _parse_request_date(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


@router.post(
    "/runs", response_model=OptimizationResponse, status_code=status.HTTP_201_CREATED
)
async def start_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    user_id: int = 1,  # TODO: Get from auth
):
    """
    Start a new optimization run.

    Creates an optimization job and runs it in the background.
    Progress can be monitored via WebSocket.
    """
    try:
        # Calculate total combinations
        if request.method == "grid":
            total_combinations = 1
            for param in request.parameters:
                if param.step:
                    count = int((param.max - param.min) / param.step) + 1
                    total_combinations *= count
                else:
                    total_combinations *= 2  # Just min and max
        else:
            total_combinations = request.n_iter or 0

        # Get strategy info
        # For now, we'll use placeholder values
        strategy_name = f"Strategy_{request.strategy_id}"
        strategy_version = "1.0.0"

        # Build parameter space for database
        param_space: Dict[str, List[Any]] = {}
        for param in request.parameters:
            if request.method == "grid" and param.step:
                import numpy as np

                if param.type == "int":
                    param_space[param.name] = list(
                        range(int(param.min), int(param.max) + 1, int(param.step))
                    )
                else:
                    param_space[param.name] = list(
                        np.arange(param.min, param.max + param.step, param.step)
                    )
            else:
                if param.type == "int":
                    param_space[param.name] = [
                        int(param.min),
                        int(param.max),
                    ]
                else:
                    param_space[param.name] = [param.min, param.max]

        # Create optimization run in database
        start_dt = _parse_request_date(request.start_date) or datetime.now()
        end_dt = _parse_request_date(request.end_date) or start_dt
        optimization_id = db_manager.create_optimization_run(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            optimization_type="parameter",
            optimization_method=request.method,
            start_date=start_dt,
            end_date=end_dt,
            symbols=[request.symbol],
            timeframes=[request.timeframe],
            parameter_space=param_space,
            objective_function=request.objective,
            total_combinations=total_combinations,
            n_jobs=request.n_jobs,
            status="pending",
        )

        logger.info(f"Created optimization run {optimization_id}")

        from apps.optimization.core import run_optimization_task

        # Add background task
        background_tasks.add_task(
            run_optimization_task,
            optimization_id=optimization_id,
            user_id=user_id,
            strategy_id=request.strategy_id,
            request=request,
            progress_manager=optimization_progress_manager,
        )

        return OptimizationResponse(
            optimization_id=optimization_id,
            status="pending",
            method=request.method,
            total_combinations=total_combinations,
            message=f"Optimization started with {total_combinations} combinations",
        )

    except Exception as e:
        logger.error(f"Error starting optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start optimization: {str(e)}",
        )


@router.get("/runs/{optimization_id}", response_model=OptimizationRunDetails)
async def get_optimization_run(optimization_id: int):
    """Get details of an optimization run."""
    try:
        run = db_manager.get_optimization_run(optimization_id)

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization run {optimization_id} not found",
            )

        return OptimizationRunDetails(**run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting optimization run: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/runs/{optimization_id}/results", response_model=List[OptimizationResultItem]
)
async def get_optimization_results(
    optimization_id: int,
    limit: int = 100,
    order_by: str = "score",
):
    """Get ranked results for an optimization run."""
    try:
        results = db_manager.get_optimization_results(
            optimization_id=optimization_id,
            limit=limit,
            order_by=order_by,
            ascending=False,
        )

        # Convert to response model
        result_items = []
        for result in results:
            result_items.append(
                OptimizationResultItem(
                    result_id=result.get("result_id", 0),
                    parameters=result.get("parameters", {}),
                    score=result.get("score", 0.0),
                    rank=result.get("rank", 0),
                    sharpe_ratio=result.get("sharpe_ratio", 0.0),
                    total_return=result.get("total_return", 0.0),
                    max_drawdown=result.get("max_drawdown", 0.0),
                    total_trades=result.get("total_trades", 0),
                    win_rate=result.get("win_rate", 0.0),
                    profit_factor=result.get("profit_factor", 0.0),
                )
            )

        return result_items

    except Exception as e:
        logger.error(f"Error getting optimization results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/runs/{optimization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_optimization(optimization_id: int):
    """Cancel a running optimization."""
    try:
        # Update status to cancelled
        success = db_manager.update_optimization_status(
            optimization_id=optimization_id,
            status="cancelled",
            completed_at=datetime.now(),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Optimization run {optimization_id} not found",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/walk-forward",
    response_model=OptimizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_walk_forward(
    request: WalkForwardRequest,
    background_tasks: BackgroundTasks,
    user_id: int = 1,
):
    """Start walk-forward analysis."""
    try:
        # Create optimization run
        strategy_name = f"Strategy_{request.strategy_id}"
        strategy_version = "1.0.0"

        param_space: Dict[str, List[Any]] = {}
        for param in request.parameters:
            if param.step:
                import numpy as np

                if param.type == "int":
                    param_space[param.name] = list(
                        range(int(param.min), int(param.max) + 1, int(param.step))
                    )
                else:
                    param_space[param.name] = list(
                        np.arange(param.min, param.max + param.step, param.step)
                    )
            else:
                if param.type == "int":
                    param_space[param.name] = [
                        int(param.min),
                        int(param.max),
                    ]
                else:
                    param_space[param.name] = [param.min, param.max]

        start_dt = _parse_request_date(request.start_date) or datetime.now()
        end_dt = _parse_request_date(request.end_date) or start_dt
        optimization_id = db_manager.create_optimization_run(
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            optimization_type="walk_forward",
            optimization_method="grid",
            start_date=start_dt,
            end_date=end_dt,
            symbols=[request.symbol],
            timeframes=[request.timeframe],
            parameter_space=param_space,
            objective_function=request.objective,
            total_combinations=0,  # Will be calculated during execution
            n_jobs=request.n_jobs,
            status="pending",
        )

        from apps.optimization.core import run_walk_forward_task

        # Add background task
        background_tasks.add_task(
            run_walk_forward_task,
            optimization_id=optimization_id,
            user_id=user_id,
            strategy_id=request.strategy_id,
            request=request,
            progress_manager=optimization_progress_manager,
        )

        return OptimizationResponse(
            optimization_id=optimization_id,
            status="pending",
            method="walk_forward",
            total_combinations=0,
            message="Walk-forward analysis started",
        )

    except Exception as e:
        logger.error(f"Error starting walk-forward analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/monte-carlo", response_model=dict, status_code=status.HTTP_201_CREATED)
async def start_monte_carlo(
    request: MonteCarloRequest,
    background_tasks: BackgroundTasks,
):
    """Start Monte Carlo simulation."""
    try:
        # Create Monte Carlo simulation record in database
        simulation_id = db_manager.create_monte_carlo_simulation(
            backtest_id=request.backtest_id,
            simulation_type=request.simulation_type,
            num_simulations=request.num_simulations,
            block_size=request.block_size,
            random_seed=request.random_seed,
        )

        from apps.optimization.core import run_monte_carlo_task

        # Add background task
        background_tasks.add_task(
            run_monte_carlo_task,
            simulation_id=simulation_id,
            request=request,
        )

        return {
            "simulation_id": simulation_id,
            "status": "pending",
            "message": f"Monte Carlo simulation started ({request.num_simulations} runs)",
        }

    except Exception as e:
        logger.error(f"Error starting Monte Carlo simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/monte-carlo/{simulation_id}", response_model=MonteCarloResponse)
async def get_monte_carlo(simulation_id: int):
    """Get Monte Carlo simulation results."""
    try:
        result = db_manager.get_monte_carlo_simulation(simulation_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monte Carlo simulation {simulation_id} not found",
            )

        return MonteCarloResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving Monte Carlo simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/monte-carlo/parametric", response_model=ParametricSimulationResult)
async def run_parametric_monte_carlo(
    request: ParametricMonteCarloRequest,
):
    """
    Run Parametric Monte Carlo simulation.

    Returns hypothetical simulation results based on statistical inputs.
    """
    try:
        result = parametric_simulation(
            win_rate=request.win_rate,
            reward_risk_ratio=request.reward_risk_ratio,
            risk_per_trade=request.risk_per_trade,
            num_trades=request.num_trades,
            num_simulations=request.num_simulations,
            initial_balance=request.initial_balance,
        )
        return result

    except Exception as e:
        logger.error(f"Error running parametric Monte Carlo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/position-sizing",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def run_position_sizing(request: PositionSizingRequest):
    """Run Position Sizing simulation (Linear vs Compounding)."""
    try:
        result = position_sizing_simulation(
            win_rate=request.win_rate,
            reward_risk_ratio=request.reward_risk_ratio,
            risk_per_trade=request.risk_per_trade,
            num_trades=request.num_trades,
            initial_balance=request.initial_balance,
        )
        return asdict(result)

    except Exception as e:
        logger.error(f"Error running position sizing simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/consecutive-losing",
    response_model=ConsecutiveLosingResponse,
    status_code=status.HTTP_200_OK,
)
async def run_consecutive_losing(request: ConsecutiveLosingRequest):
    """Run Consecutive Losing simulation for multiple systems."""
    try:
        results = consecutive_losing_simulation(
            win_rates=request.win_rates,
            rrrs=request.rrrs,
            num_trades=request.num_trades,
            num_simulations=request.num_simulations,
        )
        # Convert dataclass list to Pydantic model
        return ConsecutiveLosingResponse(
            scenarios=[ConsecutiveLosingScenario(**asdict(r)) for r in results]
        )

    except Exception as e:
        logger.error(f"Error running consecutive losing simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/profit-target",
    response_model=ProfitTargetResponse,
    status_code=status.HTTP_200_OK,
)
async def run_profit_target(request: ProfitTargetRequest):
    """Run Profit Target simulation."""
    try:
        results = profit_target_simulation(
            initial_balance=request.initial_balance,
            target_balance=request.target_balance,
            num_trades=request.num_trades,
            win_rate=request.win_rate,
            num_simulations=request.num_simulations,
        )
        return ProfitTargetResponse(
            results=[ProfitTargetResult(**asdict(r)) for r in results]
        )
    except Exception as e:
        logger.error(f"Error running profit target simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/random-win-rate",
    response_model=RandomWinRateResponse,
    status_code=status.HTTP_200_OK,
)
async def run_random_win_rate(request: RandomWinRateRequest):
    """Run Random Win Rate simulation."""
    try:
        result = random_win_rate_simulation(
            initial_equity=request.initial_equity,
            risk_per_trade=request.risk_per_trade,
            trades_per_run=request.trades_per_run,
            simulations=request.simulations,
            manual_pairs=request.manual_pairs,
        )
        return RandomWinRateResponse(result=result)
    except Exception as e:
        logger.error(f"Error running random win rate simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/robustness",
    response_model=RobustnessResponse,
    status_code=status.HTTP_200_OK,
)
async def run_robustness(request: RobustnessRequest):
    """Run Robustness simulation."""
    try:
        from apps.optimization.monte_carlo import robustness_simulation

        result = robustness_simulation(
            backtest_id=request.backtest_id,
            simulations=request.simulations,
            simulation_type=request.simulation_type,
            skip_probability=request.skip_probability,
            deterioration_pct=request.deterioration_pct,
        )
        return RobustnessResponse(**result)
    except Exception as e:
        logger.error(f"Error running robustness simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/monte-carlo/multi-entry",
    response_model=MultiEntryResponse,
    status_code=status.HTTP_200_OK,
)
async def run_multi_entry(request: MultiEntryRequest):
    """Run Multi-Entry simulation."""
    try:
        from apps.optimization.monte_carlo import multi_entry_simulation

        result = multi_entry_simulation(request)
        return result
    except Exception as e:
        logger.error(f"Error running multi-entry simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.websocket("/ws/{optimization_id}")
async def optimization_progress_websocket(websocket: WebSocket, optimization_id: int):
    """Websocket endpoint for real-time optimization progress updates."""
    await optimization_progress_manager.connect(optimization_id, websocket)
    try:
        while True:
            # Keep connection alive and wait for messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await optimization_progress_manager.disconnect(optimization_id, websocket)

