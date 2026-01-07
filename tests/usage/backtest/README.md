# Backtest Usage Examples

Comprehensive usage examples demonstrating the HaruQuant backtest module capabilities.

## Overview

This directory contains 7 progressive examples showing how to use the backtest module for trading strategy validation:

1. **Basic Backtest** - Minimal working example
2. **Finance Metrics** - Comprehensive performance analytics
3. **Plotting Results** - Visualization capabilities
4. **Comprehensive Analysis** - Complete end-to-end workflow
5. **Optimization** - Parameter optimization workflows
6. **Walk-Forward** - Robust out-of-sample validation
7. **Portfolio Backtest** - Multi-asset portfolio backtesting

## Prerequisites

### Required Modules

All examples require the following HaruQuant modules:

- `apps.backtest` - Backtesting engines and results
- `apps.finance` - Performance metrics and analytics
- `apps.plotting` - Visualization and reporting
- `apps.strategy` - Base strategy classes
- `data.strategies` - Example strategies (TrendFollowingStrategy)

### Python Dependencies

```bash
pandas
numpy
matplotlib  # For plotting
seaborn     # For advanced visualizations (optional)
bokeh       # For interactive plots (optional)
```

## Quick Start

### Run All Examples

```powershell
# From the project root
cd tests/usage/backtest

# Run each example
python 01_basic_backtest.py
python 02_finance_metrics.py
python 03_plotting_results.py
python 04_comprehensive_analysis.py
python 05_optimization.py
python 06_walk_forward.py
python 07_portfolio_backtest.py
```

### Expected Output

Each example will:
- Print detailed console output
- Create files in `output/` directory
- Generate plots and reports (where applicable)

## Example Descriptions

### 01_basic_backtest.py

**Purpose**: Learn the fundamental backtest workflow

**What it demonstrates**:
- Loading OHLC data
- Initializing a strategy with parameters
- Running EventDrivenEngine
- Accessing basic results

**Output**:
- Console summary with key metrics
- No files generated

**Complexity**: ⭐ Beginner

**Runtime**: ~5 seconds

---

### 02_finance_metrics.py

**Purpose**: Explore comprehensive performance analytics

**What it demonstrates**:
- Using all `apps.finance` submodules
- Calculating 40+ performance metrics
- Return, risk, drawdown, and trade statistics
- Distribution analysis

**Output**:
- Detailed console output organized by category
- No files generated

**Complexity**: ⭐⭐ Intermediate

**Runtime**: ~5 seconds

**Key Metrics Covered**:
- Returns: Total return, CAGR
- Ratios: Sharpe, Sortino, Calmar, Omega
- Drawdowns: Max DD, duration, recovery factor, Ulcer index
- Trades: Win rate, profit factor, expectancy, R/R ratio
- Risks: Volatility, VaR, CVaR
- Efficiency: Profit per day, capital efficiency
- Distributions: Skewness, kurtosis, normality tests

---

### 03_plotting_results.py

**Purpose**: Create professional visualizations

**What it demonstrates**:
- Using `apps.plotting` functions
- Creating individual plots
- Generating HTML reports
- Saving plots to files

**Output**:
- `output/equity_curve.png`
- `output/drawdown.png`
- `output/monthly_heatmap.png`
- `output/returns_distribution.png`
- `output/rolling_sharpe.png`
- `output/backtest_report.html`

**Complexity**: ⭐⭐ Intermediate

**Runtime**: ~10 seconds

---

### 04_comprehensive_analysis.py

**Purpose**: Complete end-to-end professional workflow

**What it demonstrates**:
- Combining backtest, finance, and plotting
- Creating structured output directories
- Saving metrics to text files
- Exporting trade history to CSV
- Generating comprehensive HTML reports

**Output**:
- `output/comprehensive_YYYYMMDD_HHMMSS/` directory containing:
  - `metrics_summary.txt`
  - `trades_history.csv`
  - `equity_curve.png`
  - `drawdown.png`
  - `monthly_returns.png`
  - `returns_distribution.png`
  - `comprehensive_report.html`

**Complexity**: ⭐⭐⭐ Advanced

**Runtime**: ~15 seconds

**Best for**: Production-ready analysis workflows

---

### 05_optimization.py

**Purpose**: Find optimal strategy parameters

**What it demonstrates**:
- Grid search optimization
- Multiple scoring functions (Sharpe, Sortino, custom)
- Using VectorizedEngine for speed
- Analyzing optimization results
- Validating with EventDrivenEngine

**Output**:
- `output/optimization_sharpe.csv`
- `output/optimization_sortino.csv`
- `output/optimization_custom.csv`
- Console output with top N results

**Complexity**: ⭐⭐⭐⭐ Advanced

**Runtime**: ~60 seconds (tests 45 parameter combinations)

**Key Concepts**:
- Parameter grid definition
- Scoring function selection
- Avoiding overfitting
- Validation with high-fidelity engine

---

### 06_walk_forward.py

**Purpose**: Robust out-of-sample validation

**What it demonstrates**:
- Walk-forward analysis methodology
- Rolling window optimization
- In-sample vs out-of-sample testing
- Parameter stability analysis
- Performance degradation assessment

**Output**:
- `output/walk_forward_results.csv`
- Console output with window-by-window results
- Parameter stability analysis

**Complexity**: ⭐⭐⭐⭐⭐ Expert

**Runtime**: ~90 seconds

**Key Metrics**:
- Train vs test score comparison
- Performance degradation percentage
- Parameter stability across windows

**Best for**: Validating strategy robustness before live trading

---

### 07_portfolio_backtest.py

**Purpose**: Multi-asset portfolio backtesting

**What it demonstrates**:
- Portfolio-level backtesting
- Multiple strategies on different assets
- Correlation analysis
- Diversification benefits
- Portfolio risk management

**Output**:
- Console output with:
  - Portfolio performance
  - Individual asset performance
  - Asset contributions
  - Correlation matrix
  - Diversification analysis

**Complexity**: ⭐⭐⭐⭐ Advanced

**Runtime**: ~20 seconds

**Key Concepts**:
- AssetSpecification configuration
- PortfolioStrategy creation
- PortfolioEngine usage
- Correlation and diversification metrics

---

## Common Patterns

### Loading Data

All examples use a `create_sample_data()` function for demonstration. In real usage, load data from:

```python
# Dukascopy API
from apps.dukascopy_api import DukascopyAPI
api = DukascopyAPI()
data = api.get_data('EURUSD', 'H1', '2024-01-01', '2024-12-31')

# CSV file
data = pd.read_csv('data.csv', index_col='timestamp', parse_dates=True)

# Database
from apps.sqlite import DatabaseManager
db = DatabaseManager()
data = db.load_ohlc_data('EURUSD', 'H1', start_date, end_date)
```

### Strategy Configuration

```python
from data.strategies.trend_following import TrendFollowingStrategy

strategy = TrendFollowingStrategy(params={
    'symbol': 'EURUSD',
    'fast_period': 20,
    'slow_period': 50,
    'filter_period': 200
})
```

### Running Backtest

```python
from apps.backtest import EventDrivenEngine

engine = EventDrivenEngine(
    strategy=strategy,
    data=data,
    initial_balance=10000.0,
    commission=7.0,
    slippage_points=1.0,
    timeframe='H1'
)

result = engine.run()
```

### Accessing Results

```python
# Basic metrics
print(f"Return: {result.total_return_pct():.2f}%")
print(f"Max DD: {result.max_drawdown_pct():.2f}%")
print(f"Win Rate: {result.win_rate():.2f}%")

# Trade history
for trade in result.trades:
    print(f"{trade.entry_time}: {trade.direction} @ {trade.entry_price}")

# Equity curve
equity_series = result._get_equity_series()
returns_series = result._get_returns_series()
```

## Troubleshooting

### Common Issues

#### Import Errors

```
ModuleNotFoundError: No module named 'apps'
```

**Solution**: Ensure you're running from the correct directory or add project root to path:

```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
```

#### No Trades Executed

```
Warning: No trades executed, metrics will be limited
```

**Causes**:
- Insufficient data for strategy warmup
- Strategy parameters too restrictive
- Data quality issues

**Solution**: Check data length and strategy requirements:

```python
# Check required warmup
warmup = max(strategy.fast_period, strategy.slow_period, strategy.filter_period)
print(f"Required warmup: {warmup} bars")
print(f"Data length: {len(data)} bars")
```

#### Plotting Errors

```
Error: Could not create plot
```

**Solution**: Ensure plotting dependencies are installed:

```bash
pip install matplotlib seaborn
```

## Best Practices

### 1. Always Use Walk-Forward for Validation

Don't rely solely on in-sample optimization. Use walk-forward analysis (example 06) to validate robustness.

### 2. Validate with EventDrivenEngine

Use VectorizedEngine for optimization speed, but always validate final parameters with EventDrivenEngine for accuracy.

### 3. Check for Overfitting

- Monitor performance degradation (train vs test)
- Ensure parameter stability across windows
- Test on out-of-sample data

### 4. Analyze Multiple Metrics

Don't optimize for a single metric. Consider:
- Return AND risk (Sharpe, Sortino)
- Drawdown characteristics
- Trade statistics
- Stability over time

### 5. Document Your Analysis

Use example 04 as a template for creating comprehensive reports with:
- Strategy parameters
- Performance metrics
- Visualizations
- Trade history

## Next Steps

After running these examples:

1. **Modify Parameters**: Experiment with different strategy parameters
2. **Use Real Data**: Replace sample data with actual market data
3. **Create Custom Strategies**: Build your own strategies using `apps.strategy.BaseStrategy`
4. **Optimize Your Strategy**: Use examples 05 and 06 to find optimal parameters
5. **Build Portfolios**: Combine multiple strategies using example 07

## Additional Resources

- **Backtest Module README**: `apps/backtest/README.md`
- **Finance Module**: `apps/finance/`
- **Plotting Module**: `apps/plotting/`
- **Strategy Development**: `apps/strategy/`

## Support

For issues or questions:
1. Check the main backtest README: `apps/backtest/README.md`
2. Review module documentation
3. Examine the example source code for detailed comments

---

**Last Updated**: 2026-01-07

**Version**: 1.0.0
