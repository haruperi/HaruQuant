"""
Backtest Module.

Event-driven and vectorized backtesting for trading strategies.

Core Components:
- EventDrivenEngine: High-fidelity bar-by-bar execution
- VectorizedEngine: Fast bulk evaluation for research
- BacktestResult: Comprehensive result tracking
- stats: Performance analytics (Sharpe, Sortino, drawdown, etc.)
- plotting: Visualization (equity curves, drawdown charts, reports)
- plotting_advanced: Advanced visualization (heatmaps, MAE/MFE, correlation, dashboards)
- optimization: Parameter optimization (grid search, random search, walk-forward)
- position_sizing: Dynamic position sizing (fixed risk, Kelly, volatility, fixed fractional)
- benchmark: Benchmark comparison (buy-hold, alpha, beta, information ratio)
- statistical_tests: Statistical validation (permutation, bootstrap, deflated Sharpe, stability)
- transaction_costs: Realistic cost modeling (commission, slippage, spread)
- persistence: Database persistence (save/load results, query backtests, optimization tracking)

Quick Example:
    ```python
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'examples'))
    from strategy.trend_following import TrendFollowingStrategy
    from apps.backtest import EventDrivenEngine

    # Create strategy with params dict
    strategy = TrendFollowingStrategy(params={
        'symbol': 'EURUSD',
        'ema_fast': 20,
        'ema_slow': 50
    })

    # Run backtest
    engine = EventDrivenEngine(strategy, data)
    result = engine.run()

    # Analyze results
    print(result.summary())
    ```
"""

from . import portfolio
from .engine import BaseEngine, EventDrivenEngine, VectorizedEngine
from .result import BacktestResult, EquityPoint, TradeRecord

__version__ = "3.4.0"

__all__ = [
    # Engines
    "BaseEngine",
    "EventDrivenEngine",
    "VectorizedEngine",
    # Results
    "BacktestResult",
    "TradeRecord",
    "EquityPoint",
    # Portfolio
    "portfolio",
]
