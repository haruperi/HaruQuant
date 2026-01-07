"""
Pydantic Models for Optimization API.

Request and response models for the optimization endpoints.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ParameterRange(BaseModel):
    """Parameter range for optimization."""

    name: str = Field(..., description="Parameter name")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    step: Optional[float] = Field(
        None, description="Step size for grid search (optional)"
    )
    type: Literal["int", "float"] = Field("float", description="Parameter type")


class OptimizationRequest(BaseModel):
    """Request to start an optimization run."""

    strategy_id: int = Field(..., description="Strategy ID to optimize")
    method: Literal["grid", "random", "bayesian", "genetic"] = Field(
        ..., description="Optimization method"
    )
    objective: Literal[
        "sharpe", "sortino", "calmar", "profit_factor", "total_return"
    ] = Field(..., description="Objective function to optimize")

    # Data configuration
    symbol: str = Field(..., description="Trading symbol (e.g., EURUSD)")
    timeframe: str = Field(..., description="Timeframe (e.g., H1, D1)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(10000.0, description="Initial capital")
    data_source: str = Field("mt5", description="Data source (mt5 or dukascopy)")

    # Parameter space
    parameters: List[ParameterRange] = Field(
        ..., description="Parameter ranges to optimize"
    )

    # Method-specific settings
    n_iter: Optional[int] = Field(
        100, description="Number of iterations (random search)"
    )
    n_initial_points: Optional[int] = Field(
        10, description="Initial random points (Bayesian)"
    )
    population_size: Optional[int] = Field(50, description="Population size (genetic)")
    generations: Optional[int] = Field(
        30, description="Number of generations (genetic)"
    )
    mutation_rate: Optional[float] = Field(0.1, description="Mutation rate (genetic)")
    crossover_rate: Optional[float] = Field(0.8, description="Crossover rate (genetic)")

    # Execution settings
    n_jobs: int = Field(-1, description="Number of parallel jobs (-1 for all cores)")
    engine_type: Literal["event_driven", "vectorized"] = Field(
        "vectorized", description="Backtest engine type"
    )


class OptimizationResponse(BaseModel):
    """Response after starting an optimization."""

    optimization_id: int = Field(..., description="Optimization run ID")
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = Field(
        ..., description="Current status"
    )
    method: str = Field(..., description="Optimization method used")
    total_combinations: int = Field(..., description="Total parameter combinations")
    message: str = Field(..., description="Status message")


class OptimizationRunDetails(BaseModel):
    """Detailed information about an optimization run."""

    optimization_id: int
    strategy_name: str
    strategy_version: str
    optimization_type: str
    optimization_method: str
    start_date: str
    end_date: str
    symbols: Optional[List[str]]
    timeframes: Optional[List[str]]
    parameter_space: Dict[str, Any]
    objective_function: str
    total_combinations: int
    completed_combinations: Optional[int]
    n_jobs: int
    status: str
    best_backtest_id: Optional[int]
    best_score: Optional[float]
    best_parameters: Optional[Dict[str, Any]]
    created_at: str
    completed_at: Optional[str]


class OptimizationResultItem(BaseModel):
    """Individual optimization result."""

    result_id: int
    parameters: Dict[str, Any]
    score: float
    rank: int
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    profit_factor: float


class WalkForwardRequest(BaseModel):
    """Request to start walk-forward analysis."""

    strategy_id: int = Field(..., description="Strategy ID to analyze")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Timeframe")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    data_source: str = Field("mt5", description="Data source (mt5 or dukascopy)")

    # Walk-forward settings
    train_period: int = Field(..., description="Training window size (bars)")
    test_period: int = Field(..., description="Testing window size (bars)")

    # Parameter space
    parameters: List[ParameterRange] = Field(..., description="Parameter ranges")
    objective: Literal["sharpe", "sortino", "calmar", "profit_factor"] = Field(
        "sharpe", description="Objective function"
    )

    # Execution
    n_jobs: int = Field(-1, description="Number of parallel jobs")
    initial_capital: float = Field(10000.0, description="Initial capital")


class WalkForwardWindow(BaseModel):
    """Walk-forward analysis window result."""

    window_id: int
    window_number: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    best_parameters: Dict[str, Any]
    train_return: float
    train_sharpe: float
    train_drawdown: float
    test_return: float
    test_sharpe: float
    test_drawdown: float
    overfitting_ratio: Optional[float]


class MonteCarloRequest(BaseModel):
    """Request to start Monte Carlo simulation."""

    backtest_id: int = Field(..., description="Backtest ID to analyze")
    simulation_type: Literal["shuffle_trades", "resample_returns", "bootstrap"] = Field(
        ..., description="Simulation method"
    )
    num_simulations: int = Field(1000, description="Number of simulations")
    block_size: Optional[int] = Field(10, description="Block size for bootstrap")
    random_seed: Optional[int] = Field(
        None, description="Random seed for reproducibility"
    )


class MonteCarloResponse(BaseModel):
    """Monte Carlo simulation results."""

    simulation_id: int
    backtest_id: int
    simulation_type: str
    num_simulations: int

    # Summary statistics (optional until simulation completes)
    mean_return: Optional[float] = None
    median_return: Optional[float] = None
    std_return: Optional[float] = None

    # Confidence intervals
    ci_95_lower: Optional[float] = None
    ci_95_upper: Optional[float] = None
    ci_99_lower: Optional[float] = None
    ci_99_upper: Optional[float] = None

    # Risk metrics
    probability_of_profit: Optional[float] = None
    probability_of_ruin: Optional[float] = None
    expected_shortfall_95: Optional[float] = None

    # Percentiles
    percentile_5: Optional[float] = None
    percentile_25: Optional[float] = None
    percentile_50: Optional[float] = None
    percentile_75: Optional[float] = None
    percentile_95: Optional[float] = None

    # Original metrics
    original_return: Optional[float] = None
    original_sharpe: Optional[float] = None
    original_max_dd: Optional[float] = None

    created_at: str
