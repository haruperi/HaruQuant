# Advanced Features Examples

This folder contains examples demonstrating advanced backtesting features for sophisticated strategy development and analysis.

## Overview

Advanced features extend the basic backtesting capabilities with:
- **Fractional Trading**: Trade fractional shares/units (crypto, stocks)
- **Multi-Asset Portfolios**: Backtest multiple instruments simultaneously
- **Optimization**: Find optimal strategy parameters
- **Walk-Forward Analysis**: Validate strategy robustness over time
- **Monte Carlo Simulation**: Assess strategy risk and confidence

All examples use **REAL data** from Dukascopy/MT5.

## Examples

### 01_fractional_trading.py
Demonstrate fractional position sizing for crypto and stock trading:
- Use `FractionalBacktest` class
- Trade fractional units (e.g., 0.5 BTC)
- Compare with standard integer-based trading
- Real crypto price data

**When to use**: Crypto trading, small accounts, precise position sizing

### 02_multi_asset.py
Backtest portfolios with multiple instruments:
- Use `MultiBacktest` class
- Trade 3+ currency pairs simultaneously
- Aggregate portfolio statistics
- Correlation and diversification analysis
- Risk distribution across assets

**When to use**: Portfolio strategies, diversification, multi-market trading

### 03_optimization.py
Find optimal strategy parameters:
- Grid search over parameter ranges
- Constraint functions
- Performance heatmaps
- Overfitting detection
- Best parameter selection

**When to use**: Parameter tuning, strategy development, performance improvement

### 04_walk_forward.py
Validate strategy robustness:
- In-sample optimization
- Out-of-sample testing
- Rolling window analysis
- Performance degradation tracking
- Realistic performance expectations

**When to use**: Strategy validation, avoiding overfitting, production deployment

### 05_monte_carlo.py
Assess strategy risk:
- Trade sequence resampling
- Multiple equity path generation
- Confidence intervals
- Risk of ruin calculation
- Worst-case scenarios

**When to use**: Risk assessment, position sizing, understanding variability

## Quick Start

```python
from apps.backtest import FractionalBacktest, MultiBacktest, Strategy
from data_helpers import load_dukascopy

# Fractional trading
data = load_dukascopy('BTCUSD', start_date='2025-11-03')
bt = FractionalBacktest(data, MyStrategy, cash=10000)
result = bt.run()

# Multi-asset portfolio
symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
datasets = {s: load_dukascopy(s, start_date='2025-11-03') for s in symbols}
bt = MultiBacktest(datasets, MyStrategy, cash=10000)
results = bt.run()

# Optimization
bt = Backtest(data, MyStrategy, cash=10000)
stats = bt.optimize(
    fast_period=range(5, 20, 5),
    slow_period=range(20, 50, 10),
    maximize='Sharpe Ratio'
)

# Walk-forward
from apps.backtest.analysis import walk_forward_analysis
results = walk_forward_analysis(
    data, MyStrategy,
    train_period=180,  # days
    test_period=60,
    step=30
)

# Monte Carlo
from apps.backtest.analysis import monte_carlo_simulation
paths = monte_carlo_simulation(
    result.trades_df,
    n_simulations=1000,
    initial_capital=10000
)
```

## Performance Considerations

### Fractional Trading
- **Speed**: Similar to standard backtest
- **Memory**: Minimal overhead
- **Use case**: Any strategy with fractional sizing

### Multi-Asset
- **Speed**: Slower (runs multiple backtests)
- **Memory**: Higher (multiple datasets)
- **Optimization**: Run backtests in parallel if possible

### Optimization
- **Speed**: Slow (many parameter combinations)
- **Memory**: Moderate
- **Tips**: 
  - Limit parameter ranges
  - Use constraints to reduce search space
  - Consider random search for large spaces

### Walk-Forward
- **Speed**: Very slow (multiple optimizations)
- **Memory**: Moderate
- **Tips**:
  - Use smaller parameter ranges
  - Increase step size for faster results
  - Cache intermediate results

### Monte Carlo
- **Speed**: Fast (resamples existing trades)
- **Memory**: Low to moderate
- **Tips**:
  - 1000 simulations usually sufficient
  - More simulations = better confidence intervals

## Best Practices

### 1. Start Simple
- Test with standard `Backtest` first
- Add advanced features when needed
- Understand basic results before optimization

### 2. Avoid Overfitting
- Use walk-forward analysis
- Test on out-of-sample data
- Don't over-optimize parameters
- Keep strategies simple

### 3. Validate Results
- Check if results make sense
- Compare with buy-and-hold
- Verify trade logic manually
- Use Monte Carlo for confidence

### 4. Performance Optimization
- Limit parameter ranges in optimization
- Use parallel processing when available
- Cache data loading
- Profile slow strategies

### 5. Risk Management
- Use Monte Carlo to understand variability
- Calculate risk of ruin
- Size positions appropriately
- Understand worst-case scenarios

## Common Pitfalls

### Optimization
❌ **Don't**: Optimize on all available data
✅ **Do**: Reserve out-of-sample data for validation

❌ **Don't**: Use too many parameters
✅ **Do**: Keep strategies simple (2-4 parameters max)

❌ **Don't**: Choose parameters with best return
✅ **Do**: Choose robust parameters (good across ranges)

### Walk-Forward
❌ **Don't**: Use very short test periods
✅ **Do**: Use realistic test periods (30-90 days)

❌ **Don't**: Ignore degradation
✅ **Do**: Expect some performance drop

### Monte Carlo
❌ **Don't**: Assume past trades predict future
✅ **Do**: Use as risk assessment tool only

❌ **Don't**: Run too few simulations
✅ **Do**: Use at least 1000 simulations

## Advanced Topics

### Parameter Constraints
```python
def constraint(params):
    # Fast MA must be less than slow MA
    return params['fast'] < params['slow']

stats = bt.optimize(
    fast=range(5, 30),
    slow=range(20, 100),
    constraint=constraint
)
```

### Custom Optimization Metrics
```python
# Optimize for risk-adjusted return
stats = bt.optimize(
    param1=range(10, 50),
    maximize=lambda s: s['Return [%]'] / s['Max. Drawdown [%]']
)
```

### Parallel Optimization
```python
# Use method='parallel' for faster optimization
stats = bt.optimize(
    param1=range(10, 100),
    param2=range(5, 50),
    maximize='Sharpe Ratio',
    method='parallel'  # If supported
)
```

## Next Steps

After mastering advanced features:
1. Explore **Statistics** examples for custom metrics
2. Learn **Visualization** for better result presentation
3. Study **Complete Workflows** for production strategies
4. Build your own advanced strategies

## Resources

- **Documentation**: `docs/apps/backtest_user_guide.md`
- **API Reference**: `docs/apps/backtest_api.md`
- **Basic Examples**: `examples/backtest/00_getting_started/`
- **Strategy Examples**: `examples/backtest/01_strategies/`
- **Data Integration**: `examples/backtest/02_data_integration/`

## Support

For questions or issues:
- Check documentation first
- Review example code
- Test with simple strategies
- Report bugs via GitHub Issues
