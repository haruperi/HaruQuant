# Statistics Examples

Examples demonstrating custom metrics, trade analysis, and performance statistics.

## Examples

### 00_stats_exammples.py
Comprehensive statistics walkthrough with real data and charts.

### 01_custom_metrics.py
Calculate custom performance metrics beyond standard statistics.

### 02_trade_analysis.py
Analyze individual trades and trading patterns.

### 03_drawdown_analysis.py
Deep dive into drawdown periods and recovery.

### 04_risk_metrics.py
Calculate risk-adjusted performance metrics.

### 05_performance_attribution.py
Attribute performance to different factors.

### 06_cache_examples.py
Demonstrate stats caching benefits and cache management.

### 07_greek_calculations.py
Greek calculations (alpha, beta, R-squared) with rolling analysis.

### 08_stats_utilities.py
Utility helpers for returns prep, alignment, formatting, and cache keys.

## Quick Start

```python
from apps.backtest import Backtest, Strategy
from apps.utils.data_getters import load_mt5

data = load_mt5('EURUSD', timeframe='D1', start_date='2025-11-03')
bt = Backtest(data, MyStrategy, cash=10000)
result = bt.run()

# Access statistics
stats = result.stats
print(f"Sharpe: {stats['Sharpe Ratio']}")
print(f"Return: {stats['Total Return [%]']}%")
```

## Key Metrics

- **Return Metrics**: Total return, CAGR, monthly/yearly returns
- **Risk Metrics**: Sharpe, Sortino, Calmar ratios
- **Drawdown**: Max drawdown, avg drawdown, recovery time
- **Trade Stats**: Win rate, avg trade, profit factor
- **Custom**: Any metric you can calculate

All examples use real MT5 data (with Dukascopy fallback).
