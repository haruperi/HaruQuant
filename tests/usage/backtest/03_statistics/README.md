# Statistics Examples

Examples demonstrating custom metrics, trade analysis, and performance statistics.

## Examples

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

## Quick Start

```python
from apps.backtest import Backtest, Strategy
from data_helpers import load_dukascopy

data = load_dukascopy('EURUSD', start_date='2025-11-03')
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

All examples use real Dukascopy data.
