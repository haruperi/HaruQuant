"""
Optimization Core.

Background task execution for optimization, walk-forward analysis, and Monte Carlo simulation.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.common.logger import logger
from backend.data.database.sqlite.database_operations import DatabaseManager
from backend.services.strategy.storage import StrategyStorage
from backend.services.strategy.permissions import assert_strategy_allowed
from backend.services.market_data.data_getters import load_dukascopy
from backend.services.market_data.data_validator import DataValidator
from backend.services.modeling import (
    UnsupervisedResearchConfig,
    UnsupervisedResearchService,
)

from .methods import (
    bayesian_optimization,
    genetic_algorithm,
    grid_search,
    random_search,
)
from .models import MonteCarloRequest, OptimizationRequest, WalkForwardRequest
from .monte_carlo import monte_carlo_analysis
from .scoring import calmar_score, profit_factor_score, sharpe_score, sortino_score


class BacktestDatabase:
    """Dummy class when module missing."""

    def save_result(self, *args, **kwargs):
        """Save result dummy method."""
        pass

    def load_result(self, *args, **kwargs):
        """Load result dummy method."""
        return None


# Map objective names to scoring functions
OBJECTIVE_FUNCTIONS = {
    "sharpe": sharpe_score,
    "sortino": sortino_score,
    "calmar": calmar_score,
    "profit_factor": profit_factor_score,
}


def _unsupervised_config_payload(config: Any) -> Optional[Dict[str, Any]]:
    if config is None:
        return None
    if hasattr(config, "model_dump"):
        payload = config.model_dump()
    elif isinstance(config, dict):
        payload = dict(config)
    else:
        return None
    if not payload.get("enabled"):
        return None
    return payload


def _build_unsupervised_config(config_payload: Optional[Dict[str, Any]]) -> Optional[UnsupervisedResearchConfig]:
    if not config_payload:
        return None
    return UnsupervisedResearchConfig(
        fast_period=int(config_payload.get("fast_period", 20)),
        slow_period=int(config_payload.get("slow_period", 50)),
        volatility_window=int(config_payload.get("volatility_window", 20)),
        momentum_window=int(config_payload.get("momentum_window", 5)),
        min_feature_periods=int(config_payload.get("min_feature_periods", 3)),
        include_ema_spread=bool(config_payload.get("include_ema_spread", True)),
        n_components=int(config_payload.get("n_components", 2)),
        n_clusters=int(config_payload.get("n_clusters", 3)),
        random_state=int(config_payload.get("random_state", 42)),
        forward_return_horizon=int(config_payload.get("forward_return_horizon", 1)),
        label_column=str(config_payload.get("label_column", "cluster_label")),
        price_column=str(config_payload.get("price_column", "close")),
        min_rows=int(config_payload.get("min_rows", 25)),
        min_cluster_observations=int(config_payload.get("min_cluster_observations", 3)),
        scale_features=bool(config_payload.get("scale_features", True)),
        enable_signal_adaptation=bool(config_payload.get("enable_signal_adaptation", False)),
    )


def _run_unsupervised_analysis(
    data: Any,
    config_payload: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    config = _build_unsupervised_config(config_payload)
    if config is None:
        return None
    if data is None or getattr(data, "empty", True):
        return {
            "status": "SKIPPED",
            "config": config.to_dict(),
            "reason": "no market data available for unsupervised analysis",
        }
    service = UnsupervisedResearchService()
    result = service.analyze_frame(data, config=config)
    return result.to_metadata()


def _parse_request_date(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported date value: {value!r}")


async def run_optimization_task(  # noqa: C901
    optimization_id: int,
    user_id: int,
    strategy_id: int,
    request: OptimizationRequest,
    progress_manager=None,
) -> None:
    """
    Background task for parameter optimization.

    Args:
        optimization_id: Database ID for this optimization run
        user_id: User ID
        strategy_id: Strategy ID to optimize
        request: Optimization request with parameters
        progress_manager: OptimizationProgressManager for WebSocket updates
    """
    db_manager = DatabaseManager()
    backtest_db = BacktestDatabase()
    storage = StrategyStorage()
    unsupervised_config = _unsupervised_config_payload(getattr(request, "unsupervised", None))

    loop = asyncio.get_event_loop()

    try:
        # Update status to running
        db_manager.update_optimization_status(
            optimization_id,
            "running",
            unsupervised_status="pending" if unsupervised_config else None,
        )
        assert_strategy_allowed(strategy_id, "optimization", db_manager=db_manager)

        logger.info(
            f"Starting optimization {optimization_id} (method: {request.method})"
        )

        # Get strategy info from database to get version
        strategy_info = db_manager.get_strategy(strategy_id)

        if not strategy_info:
            raise ValueError(f"Strategy with id {strategy_id} not found")

        # Extract version and metadata
        version = strategy_info.get("active_version", "1.0.0")
        if not version:
            version = "1.0.0"  # Default if no active version

        # Get user info to get username
        user_info = db_manager.get_user(user_id)
        if not user_info:
            raise ValueError(f"User with id {user_id} not found")

        username = user_info.get("username", "")
        if not username:
            raise ValueError("Username cannot be empty")

        # Load strategy class with version
        strategy_class = storage.load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            username=username,
            strategy_name=strategy_info.get("name", ""),
        )

        # Get strategy file path for parallel execution
        strategy_path = storage.get_strategy_path(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            username=username,
            strategy_name=strategy_info.get("name", ""),
        )

        # Load data based on source
        data_source = (
            request.data_source.lower() if hasattr(request, "data_source") else "mt5"
        )

        logger.info(
            f"Loading data from {data_source}: {request.symbol} {request.timeframe}"
        )

        if data_source in ["metatrader5", "mt5"]:
            try:
                from backend.mcp.mt5_mcp.client import MT5Client
                from backend.data.database.sqlite.users import UserManager

                creds = UserManager().get_mt5_credentials(user_id) or {}
                login = int(creds.get("login") or 0)
                password = creds.get("password") or ""
                server = creds.get("server") or ""
                path = creds.get("path") or ""
                if not (login and password and server):
                    raise ValueError("Missing MT5 credentials")

                client = MT5Client()
                if not client.connect(
                    path=path,
                    login=login,
                    password=password,
                    server=server,
                ):
                    raise ValueError("Failed to initialize MT5")

                data = client.get_bars(
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    date_from=_parse_request_date(request.start_date),
                    date_to=_parse_request_date(request.end_date),
                )
                client.shutdown()

                # Validate and normalize data (ensure lowercase columns)
                if data is not None and not data.empty:
                    data = DataValidator.prepare_data(data)

            except Exception as e:
                logger.error(f"MT5 data loading failed: {e}")
                raise ValueError(f"Failed to load data from MT5: {str(e)}")
        else:
            # Fallback to Dukascopy for other data sources
            data = load_dukascopy(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if data is None or data.empty:
            raise ValueError(
                f"No data loaded for {request.symbol} {request.timeframe} from {data_source}"
            )

        unsupervised_report = _run_unsupervised_analysis(data, unsupervised_config)
        if unsupervised_report is not None:
            db_manager.update_optimization_status(
                optimization_id,
                "running",
                unsupervised_status=str(unsupervised_report.get("status", "completed")).lower(),
                unsupervised_report=unsupervised_report,
                unsupervised_context={
                    "strategy_context": unsupervised_report.get("strategy_context", {}),
                    "risk_context": unsupervised_report.get("risk_context", {}),
                },
            )

        # Get scoring function
        scoring_func = OBJECTIVE_FUNCTIONS.get(request.objective, sharpe_score)

        # Build parameter grid/space
        param_grid: Dict[str, List[Any]] = {}
        param_space: Dict[str, Tuple[float, float]] = {}
        param_types: Dict[str, str] = {}

        for param in request.parameters:
            param_types[param.name] = param.type

            if request.method == "grid":
                # Grid search needs list of values
                if param.step:
                    import numpy as np

                    if param.type == "int":
                        values = list(
                            range(int(param.min), int(param.max) + 1, int(param.step))
                        )
                    else:
                        values = list(
                            np.arange(param.min, param.max + param.step, param.step)
                        )
                    param_grid[param.name] = values
                else:
                    # No step specified, use min and max only
                    if param.type == "int":
                        param_grid[param.name] = [
                            int(param.min),
                            int(param.max),
                        ]
                    else:
                        param_grid[param.name] = [param.min, param.max]
            else:
                # Other methods need (min, max) tuples
                param_space[param.name] = (param.min, param.max)

        # Helper to convert numpy types to native Python types
        def convert_to_python_type(obj):
            import numpy as np

            # Use base classes for NumPy 2.0 compatibility
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_python_type(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_python_type(i) for i in obj]
            return obj

        # Progress callback for WebSocket updates
        def progress_callback(
            completed, total, current_params, best_score, best_params
        ):
            if progress_manager:
                # Convert params to native types for JSON serialization
                safe_current_params = convert_to_python_type(current_params)
                safe_best_params = convert_to_python_type(best_params)

                asyncio.run_coroutine_threadsafe(
                    progress_manager.broadcast_progress(
                        optimization_id,
                        {
                            "type": "progress",
                            "optimization_id": optimization_id,
                            "completed": completed,
                            "total": total,
                            "percentage": (completed / total) * 100 if total > 0 else 0,
                            "current_params": safe_current_params,
                            "best_score": (
                                float(best_score)
                                if hasattr(best_score, "item")
                                else best_score
                            ),
                            "best_params": safe_best_params,
                            "timestamp": datetime.now().isoformat(),
                        },
                    ),
                    loop,
                )

        # Determine number of workers (n_jobs)
        n_jobs = (
            request.n_jobs if request.n_jobs > 0 else None
        )  # -1 means use all cores
        n_iter = request.n_iter if request.n_iter is not None else 100
        n_initial_points = (
            request.n_initial_points if request.n_initial_points is not None else 10
        )
        population_size = (
            request.population_size if request.population_size is not None else 50
        )
        generations = request.generations if request.generations is not None else 30
        mutation_rate = (
            request.mutation_rate if request.mutation_rate is not None else 0.1
        )
        crossover_rate = (
            request.crossover_rate if request.crossover_rate is not None else 0.8
        )

        # Run optimization based on method
        if request.method == "grid":
            summary = grid_search(
                strategy_class=strategy_class,
                data=data,
                param_grid=param_grid,
                initial_balance=request.initial_capital,
                scoring_func=scoring_func,
                engine_type=request.engine_type,
                max_workers=n_jobs,
                verbose=True,
                progress_callback=progress_callback,
                strategy_file_path=strategy_path,
                symbol=request.symbol,
            )
        elif request.method == "random":
            summary = random_search(
                strategy_class=strategy_class,
                data=data,
                param_distributions=param_space,
                n_iter=n_iter,
                initial_balance=request.initial_capital,
                scoring_func=scoring_func,
                engine_type=request.engine_type,
                max_workers=n_jobs,
                verbose=True,
                progress_callback=progress_callback,
                strategy_file_path=strategy_path,
                symbol=request.symbol,
            )
        elif request.method == "bayesian":
            summary = bayesian_optimization(
                strategy_class=strategy_class,
                data=data,
                param_space=param_space,
                param_types=param_types,
                n_iterations=n_iter,
                n_initial_points=n_initial_points,
                initial_balance=request.initial_capital,
                scoring_func=scoring_func,
                engine_type=request.engine_type,
                max_workers=n_jobs,
                verbose=True,
                progress_callback=progress_callback,
                symbol=request.symbol,
            )
        elif request.method == "genetic":
            summary = genetic_algorithm(
                strategy_class=strategy_class,
                data=data,
                param_ranges=param_space,
                param_types=param_types,
                population_size=population_size,
                generations=generations,
                mutation_rate=mutation_rate,
                crossover_rate=crossover_rate,
                initial_balance=request.initial_capital,
                scoring_func=scoring_func,
                engine_type=request.engine_type,
                max_workers=n_jobs,
                verbose=True,
                progress_callback=progress_callback,
                symbol=request.symbol,
            )
        else:
            raise ValueError(f"Unknown optimization method: {request.method}")

        # Save results to database
        # First, create backtest runs for each result
        backtest_ids = []

        # Get strategy name for backtest records
        strategy_info = db_manager.get_strategy(strategy_id)
        strategy_name = (
            strategy_info["name"] if strategy_info else f"Strategy_{strategy_id}"
        )

        # Generate config hash from parameters
        import hashlib
        import json

        start_dt = _parse_request_date(request.start_date) or datetime.now()
        end_dt = _parse_request_date(request.end_date) or datetime.now()

        for opt_result in summary.all_results:
            # Create config hash from optimization parameters
            config_str = json.dumps(opt_result.parameters, sort_keys=True)
            config_hash = hashlib.md5(config_str.encode()).hexdigest()

            # Create backtest run entry
            backtest_id = db_manager.create_backtest_run(
                strategy_name=strategy_name,
                strategy_version="1.0",  # Default version for optimization runs
                start_date=start_dt,
                end_date=end_dt,
                engine_type=request.engine_type,
                data_resolution=request.timeframe,
                config_hash=config_hash,
                strategy_version_id=None,
                user_id=user_id,
                symbols=[request.symbol],
                timeframes=[request.timeframe],
                initial_balance=request.initial_capital,
            )

            # Save backtest result details
            backtest_db.save_result(opt_result.result, backtest_id)
            backtest_ids.append(backtest_id)

        # Save optimization results
        results_to_save = []
        for i, opt_result in enumerate(summary.all_results):
            results_to_save.append(
                {
                    "backtest_id": backtest_ids[i],
                    "parameters": opt_result.parameters,
                    "score": opt_result.score,
                    "rank": opt_result.rank,
                    "total_trades": opt_result.result.total_trades,
                    "win_rate": opt_result.result.win_rate,
                    "profit_factor": opt_result.metrics.get("profit_factor", 0.0),
                    "sharpe_ratio": opt_result.metrics.get("sharpe_ratio", 0.0),
                    "max_drawdown": opt_result.result.max_drawdown_pct,
                    "is_best": i == 0,
                    "is_top_10": i < 10,
                    "unsupervised_report": unsupervised_report,
                }
            )

        db_manager.save_optimization_results(optimization_id, results_to_save)

        # Update optimization run with best result
        best_backtest_id = backtest_ids[0] if backtest_ids else None
        db_manager.update_optimization_status(
            optimization_id=optimization_id,
            status="completed",
            completed_combinations=summary.completed,
            best_backtest_id=best_backtest_id,
            best_score=summary.best_score,
            best_parameters=summary.best_params,
            unsupervised_status=(
                str(unsupervised_report.get("status", "completed")).lower()
                if unsupervised_report is not None
                else None
            ),
            unsupervised_report=unsupervised_report,
            unsupervised_context=(
                {
                    "strategy_context": unsupervised_report.get("strategy_context", {}),
                    "risk_context": unsupervised_report.get("risk_context", {}),
                }
                if unsupervised_report is not None
                else None
            ),
            completed_at=datetime.now(),
        )

        logger.success(f"Optimization {optimization_id} completed successfully")

    except Exception as e:
        logger.error(f"Optimization {optimization_id} failed: {e}")
        db_manager.update_optimization_status(
            optimization_id,
            "failed",
            unsupervised_status="failed" if unsupervised_config else None,
            completed_at=datetime.now(),
        )
        raise


async def run_walk_forward_task(  # noqa: C901
    optimization_id: int,
    user_id: int,
    strategy_id: int,
    request: WalkForwardRequest,
    progress_manager=None,
) -> None:
    """
    Background task for walk-forward analysis.

    Args:
        optimization_id: Database ID for this optimization run
        user_id: User ID
        strategy_id: Strategy ID to analyze
        request: Walk-forward request
        progress_manager: OptimizationProgressManager for WebSocket updates
    """
    db_manager = DatabaseManager()
    storage = StrategyStorage()
    unsupervised_config = _unsupervised_config_payload(getattr(request, "unsupervised", None))

    try:
        # Update status
        db_manager.update_optimization_status(
            optimization_id,
            "running",
            unsupervised_status="pending" if unsupervised_config else None,
        )
        assert_strategy_allowed(strategy_id, "optimization", db_manager=db_manager)

        logger.info(f"Starting walk-forward analysis {optimization_id}")

        # Get strategy info from database to get version
        strategy_info = db_manager.get_strategy(strategy_id)

        if not strategy_info:
            raise ValueError(f"Strategy with id {strategy_id} not found")

        # Extract version and metadata
        version = strategy_info.get("active_version", "1.0.0")
        if not version:
            version = "1.0.0"  # Default if no active version

        # Get user info to get username
        user_info = db_manager.get_user(user_id)
        if not user_info:
            raise ValueError(f"User with id {user_id} not found")

        username = user_info.get("username", "")
        if not username:
            raise ValueError("Username cannot be empty")

        # Load strategy class with version
        strategy_class = storage.load_strategy_class(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            username=username,
            strategy_name=strategy_info.get("name", ""),
        )
        strategy_path = storage.get_strategy_path(
            user_id=user_id,
            strategy_id=strategy_id,
            version=version,
            username=username,
            strategy_name=strategy_info.get("name", ""),
        )

        # Load data based on source
        data_source = (
            request.data_source.lower() if hasattr(request, "data_source") else "mt5"
        )

        logger.info(
            f"Loading data from {data_source}: {request.symbol} {request.timeframe}"
        )

        if data_source in ["metatrader5", "mt5"]:
            try:
                from backend.mcp.mt5_mcp.client import MT5Client
                from backend.data.database.sqlite.users import UserManager

                creds = UserManager().get_mt5_credentials(user_id) or {}
                login = int(creds.get("login") or 0)
                password = creds.get("password") or ""
                server = creds.get("server") or ""
                path = creds.get("path") or ""
                if not (login and password and server):
                    raise ValueError("Missing MT5 credentials")

                client = MT5Client()
                if not client.connect(
                    path=path,
                    login=login,
                    password=password,
                    server=server,
                ):
                    raise ValueError("Failed to initialize MT5")

                data = client.get_bars(
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    date_from=_parse_request_date(request.start_date),
                    date_to=_parse_request_date(request.end_date),
                )
                client.shutdown()

                # Validate and normalize data (ensure lowercase columns)
                if data is not None and not data.empty:
                    data = DataValidator.prepare_data(data)

            except Exception as e:
                logger.error(f"MT5 data loading failed: {e}")
                raise ValueError(f"Failed to load data from MT5: {str(e)}")
        else:
            # Fallback to Dukascopy for other data sources
            data = load_dukascopy(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=request.start_date,
                end_date=request.end_date,
            )

        if data is None or data.empty:
            raise ValueError(
                f"No data loaded for {request.symbol} {request.timeframe} from {data_source}"
            )

        unsupervised_report = _run_unsupervised_analysis(data, unsupervised_config)
        if unsupervised_report is not None:
            db_manager.update_optimization_status(
                optimization_id,
                "running",
                unsupervised_status=str(unsupervised_report.get("status", "completed")).lower(),
                unsupervised_report=unsupervised_report,
                unsupervised_context={
                    "strategy_context": unsupervised_report.get("strategy_context", {}),
                    "risk_context": unsupervised_report.get("risk_context", {}),
                },
            )

        # Build parameter grid
        param_grid: Dict[str, List[Any]] = {}
        for param in request.parameters:
            if param.step:
                import numpy as np

                if param.type == "int":
                    values = list(
                        range(int(param.min), int(param.max) + 1, int(param.step))
                    )
                else:
                    values = list(
                        np.arange(param.min, param.max + param.step, param.step)
                    )
                param_grid[param.name] = values
            else:
                if param.type == "int":
                    param_grid[param.name] = [
                        int(param.min),
                        int(param.max),
                    ]
                else:
                    param_grid[param.name] = [param.min, param.max]

        scoring_func = OBJECTIVE_FUNCTIONS.get(request.objective, sharpe_score)

        # Run walk-forward
        from .walk_forward import walk_forward

        _ = walk_forward(
            strategy_class=strategy_class,
            data=data,
            param_grid=param_grid,
            train_period=request.train_period,
            test_period=request.test_period,
            initial_balance=request.initial_capital,
            scoring_func=scoring_func,
            verbose=True,
            strategy_file_path=strategy_path,
            symbol=request.symbol,
        )

        # Save walk-forward windows to database
        # (Would need to implement save_walk_forward_windows in database)

        # Update status
        db_manager.update_optimization_status(
            optimization_id,
            "completed",
            unsupervised_status=(
                str(unsupervised_report.get("status", "completed")).lower()
                if unsupervised_report is not None
                else None
            ),
            unsupervised_report=unsupervised_report,
            unsupervised_context=(
                {
                    "strategy_context": unsupervised_report.get("strategy_context", {}),
                    "risk_context": unsupervised_report.get("risk_context", {}),
                }
                if unsupervised_report is not None
                else None
            ),
            completed_at=datetime.now(),
        )

        logger.success(f"Walk-forward analysis {optimization_id} completed")

    except Exception as e:
        logger.error(f"Walk-forward {optimization_id} failed: {e}")
        db_manager.update_optimization_status(
            optimization_id,
            "failed",
            unsupervised_status="failed" if unsupervised_config else None,
        )
        raise


async def run_monte_carlo_task(
    simulation_id: int,
    request: MonteCarloRequest,
) -> None:
    """
    Background task for Monte Carlo simulation.

    Args:
        simulation_id: Database ID for this simulation
        request: Monte Carlo request
    """
    db_manager = DatabaseManager()
    backtest_db = BacktestDatabase()

    try:
        logger.info(f"Starting Monte Carlo simulation {simulation_id}")

        # Load backtest result
        backtest_result = backtest_db.load_result(request.backtest_id)

        if not backtest_result:
            raise ValueError(f"Backtest {request.backtest_id} not found")

        # Run Monte Carlo analysis
        # Prepare kwargs based on simulation type
        mc_kwargs = {
            "result": backtest_result,
            "num_simulations": request.num_simulations,
            "simulation_type": request.simulation_type,
            "random_seed": request.random_seed,
        }

        # Only pass block_size for bootstrap simulation
        if request.simulation_type == "bootstrap" and request.block_size:
            mc_kwargs["block_size"] = request.block_size

        mc_result = monte_carlo_analysis(**mc_kwargs)

        # Prepare results dictionary for database
        results_dict = {
            "mean_return": mc_result.mean_return,
            "median_return": mc_result.median_return,
            "std_return": mc_result.std_return,
            "ci_95_lower": mc_result.ci_95_lower,
            "ci_95_upper": mc_result.ci_95_upper,
            "ci_99_lower": mc_result.ci_99_lower,
            "ci_99_upper": mc_result.ci_99_upper,
            "probability_of_profit": mc_result.probability_of_profit,
            "probability_of_ruin": mc_result.probability_of_ruin,
            "expected_shortfall_95": mc_result.expected_shortfall_95,
            "percentile_5": mc_result.percentile_5,
            "percentile_25": mc_result.percentile_25,
            "percentile_50": mc_result.percentile_50,
            "percentile_75": mc_result.percentile_75,
            "percentile_95": mc_result.percentile_95,
            "original_return": mc_result.original_return,
            "original_sharpe": mc_result.original_sharpe,
            "original_max_dd": mc_result.original_max_dd,
            "distribution_data": {
                "returns": mc_result.total_returns,
                "drawdowns": mc_result.max_drawdowns,
                "sharpes": mc_result.sharpe_ratios,
                "win_rates": mc_result.win_rates,
            },
        }

        # Save results to database
        db_manager.save_monte_carlo_results(simulation_id, results_dict)

        logger.success(f"Monte Carlo simulation {simulation_id} completed")

    except Exception as e:
        logger.error(f"Monte Carlo {simulation_id} failed: {e}")
        raise



