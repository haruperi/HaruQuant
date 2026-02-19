# Getting Started with HaruQuant Backtest

Welcome! This folder contains introductory examples to help you learn the basics of the HaruQuant backtesting system.

## What You'll Learn

This section covers the essential skills for running backtests with HaruQuant, from basic execution to deep performance analysis and implementing custom strategies. By the end of these examples, you will be able to load market data, define strategies, run event-driven simulations, and interpret detailed financial metrics.

### [01_basic_backtest.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/00_getting_started/01_basic_backtest.py)
- **Goal**: Run your first backtest in under 5 minutes.
- How to load historical data from MT5.
- Creating a simple `TrendFollowingStrategy`.
- Running the `EventDrivenEngine`.
- Viewing basic performance metrics and trade statistics.

**Perfect for:** First-time users who want to see a complete working example.

### [02_finance_metrics.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/00_getting_started/02_finance_metrics.py)
- **Goal**: Understand the wealth of data returns by a backtest.
- Detailed exploration of the `BacktestResult` object.
- Accessing comprehensive statistics (Sharpe, Sortino, Calmar, VaR, etc.).
- Analyzing return metrics, risk-adjusted ratios, and drawdown metrics.
- Detailed trade analysis including win/loss streaks and average duration.

**Perfect for:** Users who want to deeply understand the output and analytics capabilities.

### [03_pending_backtest.py](file:///d:/Trading/Applications/HaruQuant/tests/usage/backtest/00_getting_started/03_pending_backtest.py)
- **Goal**: Learn to use pending orders and more complex strategies.
- Implementing a `BreakoutStrategy` using Buy Stop / Sell Stop orders.
- Verifying order execution and handling.
- Working with different timeframes (D1 in this example).

**Perfect for:** Users ready to implement strategies that require entry stop/limit orders.

## Quick Start

### 1. Install Requirements

```bash
pip install pandas numpy matplotlib apps.backtest apps.mt5
```

### 2. Verify Data Availability

Make sure you have MT5 data available or a connection to MT5. These examples load data via the `MT5Client`.

### 3. Run Your First Backtest

```bash
python tests/usage/backtest/00_getting_started/01_basic_backtest.py
```

You should see:
- Log messages showing data loading
- Backtest execution progress
- A summary of performance statistics (Total Return, Win Rate, etc.)

## The Basic Pattern

All backtests follow this pattern:

```python
from apps.backtest import EventDrivenEngine, Strategy
from apps.mt5.client import MT5Client

# 1. Load data
# (Use MT5Client or load_parquet helpers)

# 2. Define/Configure strategy
class MyStrategy(Strategy):
    def init(self):
        pass
    def next(self):
        if not self.position:
            self.buy(size=0.1)

# 3. Create and run backtest
engine = EventDrivenEngine(
    strategy=MyStrategy(params={...}),
    data=data,
    initial_balance=10000,
    commission=7.0
)
result = engine.run()

# 4. Analyze results
print(result.total_return_pct)
```

## Understanding BacktestResult

When you run `engine.run()`, you get a `BacktestResult` object with:

- **`result.trades`** - List of executed trades
- **`result.equity`** - Array of equity values over time
- **`result.stats`** - Pre-calculated statistics object
- **`result.total_return`**, **`result.sharpe_ratio`**, etc. - Direct access to key metrics

## Key Statistics List

The `BacktestResult` object provides access to over 90+ financial metrics. Here are the most common ones:

```python
# Return Metrics
result.total_return_pct     # Total return in %
result.cagr                 # Compound Annual Growth Rate
result.daily_mean           # Average daily return

# Risk Metrics
result.max_drawdown_pct     # Maximum drawdown in %
result.volatility           # Annualized volatility
result.var_95               # Value at Risk (95% confidence)

# Ratios (Risk-Adjusted Returns)
result.sharpe_ratio         # Sharpe Ratio (Risk-free rate adjusted)
result.sortino_ratio        # Sortino Ratio (Downside risk adjusted)
result.calmar_ratio         # Calmar Ratio (Return / Max Drawdown)
result.profit_factor        # Gross Profit / Gross Loss

# Trade Statistics
result.win_rate             # Percentage of winning trades
result.avg_win              # Average winning trade amount
result.avg_loss             # Average losing trade amount
result.expectancy           # Expected value per trade
result.total_trades         # Total number of trades executed
```

## Next Steps

After completing these getting started examples:

1. **Explore `01_strategies/`** - Learn different strategy types.
2. **Check `02_data_integration/`** - Advanced data loading.
3. **Review `apps/finance/`** - Source code for the metrics calculations.
