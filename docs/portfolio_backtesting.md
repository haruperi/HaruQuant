# Portfolio Backtesting Guide

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [PortfolioStrategy](#portfoliostrategy)
  - [PortfolioEngine](#portfolioengine)
  - [PortfolioBacktestResult](#portfoliobacktestresult)
  - [DataSynchronizer](#datasynchronizer)
- [Allocation Methods](#allocation-methods)
- [Data Synchronization](#data-synchronization)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

The portfolio backtesting system allows you to backtest multiple instruments simultaneously with unified account tracking. It supports:

- **Multi-symbol execution**: Trade multiple instruments (EURUSD, GBPUSD, USDJPY, etc.) in a single backtest
- **Allocation strategies**: Equal-weight and risk-parity position sizing
- **Data synchronization**: Automatic alignment of data across symbols with different timestamps
- **Portfolio-level metrics**: Sharpe ratio, max drawdown, correlation analysis
- **Per-asset attribution**: Individual performance metrics for each symbol
- **Single account model**: Unified balance and equity tracking across all positions

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Application                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                       PortfolioEngine                           │
│  - Orchestrates multi-symbol backtest                           │
│  - Creates TradeSimulator with multiple symbols                 │
│  - Packages results into PortfolioBacktestResult                │
└─────────────────────────────────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ↓                    ↓                    ↓
  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
  │PortfolioStrategy│  │ DataSynchronizer │  │ TradeSimulator  │
  │                 │  │                  │  │                 │
  │ - Strategies    │  │ - Align data     │  │ - Positions     │
  │ - Symbol specs  │  │ - Handle gaps    │  │ - Trade records │
  │ - Data          │  │ - ffill/drop     │  │ - Account       │
  │ - Allocations   │  │                  │  │ - Execution     │
  └─────────────────┘  └──────────────────┘  └─────────────────┘
            │                    │                    │
            └────────────────────┴────────────────────┘
                                 │
                                 ↓
            ┌──────────────────────────────────────┐
            │      SimulationEngine._run_portfolio │
            │  - Bar-by-bar loop across ALL symbols│
            │  - Update ticks for all symbols      │
            │  - Process signals for each symbol   │
            │  - Update unified equity curve       │
            └──────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PortfolioBacktestResult                       │
│  - Portfolio summary (Sharpe, drawdown, total return)           │
│  - Asset results (per-symbol metrics)                           │
│  - Correlation matrix                                           │
│  - Asset contributions                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **PortfolioStrategy**: Configuration for multi-symbol backtest
   - Holds strategies for each symbol
   - Symbol specifications (SymbolInfoSimulator)
   - Historical data for each symbol
   - Allocation method (equal_weight or risk_parity)

2. **PortfolioEngine**: Orchestrates the backtest
   - Synchronizes data across symbols
   - Creates TradeSimulator with multiple symbols
   - Runs bar-by-bar simulation
   - Packages results

3. **DataSynchronizer**: Aligns multi-symbol data
   - Creates union of all timestamps
   - Reindexes each DataFrame to common timeline
   - Handles missing bars (ffill/drop/interpolate)

4. **TradeSimulator**: Executes trades (inherits from SimulationEngine)
   - Manages positions across all symbols
   - Unified account balance
   - Single equity curve

5. **PortfolioBacktestResult**: Results container
   - Portfolio-level metrics
   - Per-asset results
   - Correlation analysis
   - Asset contributions

---

## Quick Start

### Basic Example

```python
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy
import pandas as pd

# 1. Load data for multiple symbols
data = {
    'EURUSD': eurusd_df,  # pd.DataFrame with OHLCV
    'GBPUSD': gbpusd_df,
    'USDJPY': usdjpy_df,
}

# 2. Create symbol specs (using existing MT5 symbols)
symbol_specs = {
    symbol: SymbolInfoSimulator.from_mt5_symbol(symbol)
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY']
}

# 3. Create strategies for each symbol
strategies = {
    symbol: MyTrendStrategy(params={'symbol': symbol})
    for symbol in data.keys()
}

# 4. Build portfolio strategy
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'  # or 'risk_parity'
)

# 5. Run backtest
engine = PortfolioEngine(
    portfolio_strategy=portfolio_strategy,
    initial_balance=30000.0,
    config={
        'portfolio_name': 'My Multi-Asset Portfolio',
        'volume': 0.1,
        'commission': 7.0,
        'slippage': 0.5
    }
)

result = engine.run(synchronize_data=True, sync_method='ffill')

# 6. View results
summary = result.get_portfolio_summary()
print(f"Total Return: {summary['total_return_pct']:.2f}%")
print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")

# Per-asset breakdown
for symbol, asset_result in result.asset_results.items():
    print(f"{symbol}: {asset_result.total_return_pct:.2f}%")

# Correlation matrix
corr_matrix = result.get_correlation_matrix()
print(corr_matrix)
```

---

## API Reference

### PortfolioStrategy

Configuration class for multi-symbol portfolio backtesting.

#### Constructor

```python
PortfolioStrategy(
    strategies: Dict[str, BaseStrategy],
    symbol_specs: Dict[str, SymbolInfoSimulator],
    data: Dict[str, pd.DataFrame],
    max_total_exposure: float = 1.0,
    max_correlated_exposure: float = 0.6,
    allocation_method: Literal['equal_weight', 'risk_parity'] = 'equal_weight'
)
```

**Parameters:**
- `strategies`: Dictionary mapping symbol → strategy instance
- `symbol_specs`: Dictionary mapping symbol → SymbolInfoSimulator
- `data`: Dictionary mapping symbol → DataFrame (OHLCV data with DatetimeIndex)
- `max_total_exposure`: Maximum total portfolio exposure (default 1.0 = 100%)
- `max_correlated_exposure`: Maximum exposure to correlated assets (default 0.6 = 60%)
- `allocation_method`: Position sizing method ('equal_weight' or 'risk_parity')

**Raises:**
- `ValueError`: If symbol sets don't match or data is invalid

#### Methods

##### `validate() -> None`
Validates portfolio configuration. Checks that symbol sets match across strategies/specs/data and validates data format.

**Raises:**
- `ValueError`: If configuration is invalid

##### `calculate_allocations() -> Dict[str, float]`
Calculates position size allocations for each symbol based on allocation_method.

**Returns:**
- Dictionary mapping symbol → allocation weight (0.0 to 1.0)

**Example:**
```python
portfolio = PortfolioStrategy(
    strategies={'EURUSD': strategy1, 'GBPUSD': strategy2},
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'
)

allocations = portfolio.calculate_allocations()
# Returns: {'EURUSD': 0.5, 'GBPUSD': 0.5}
```

---

### PortfolioEngine

Engine for running multi-asset portfolio backtests.

#### Constructor

```python
PortfolioEngine(
    portfolio_strategy: PortfolioStrategy,
    initial_balance: float,
    config: Optional[Dict] = None
)
```

**Parameters:**
- `portfolio_strategy`: PortfolioStrategy configuration
- `initial_balance`: Starting account balance
- `config`: Optional configuration dict with keys:
  - `portfolio_name`: Name for the portfolio (default: 'Portfolio')
  - `volume`: Base volume per trade (default: 0.1)
  - `commission`: Commission per contract (default: 0.0)
  - `slippage`: Slippage in points (default: 0.0)
  - `verbose`: Enable detailed logging (default: False)
  - `simulator_name`: Name for TradeSimulator (default: 'PortfolioSimulator')

#### Methods

##### `run(synchronize_data: bool = True, sync_method: Literal['ffill', 'drop', 'interpolate'] = 'ffill') -> PortfolioBacktestResult`

Runs portfolio backtest.

**Parameters:**
- `synchronize_data`: Whether to synchronize data timelines (default True)
- `sync_method`: Method for synchronizing data (default 'ffill')
  - `'ffill'`: Forward-fill missing bars
  - `'drop'`: Drop timestamps with missing data
  - `'interpolate'`: Interpolate missing values

**Returns:**
- `PortfolioBacktestResult` with complete metrics

**Raises:**
- `ValueError`: If configuration is invalid

**Example:**
```python
engine = PortfolioEngine(portfolio_strategy, initial_balance=30000)
result = engine.run(synchronize_data=True, sync_method='ffill')
```

**Process:**
1. Validates portfolio strategy
2. Calculates position allocations
3. Synchronizes data (if enabled)
4. Creates TradeSimulator with multiple symbols
5. Runs bar-by-bar simulation
6. Packages results into PortfolioBacktestResult

---

### PortfolioBacktestResult

Results container for portfolio backtests.

#### Attributes

- `portfolio_name: str` - Name of the portfolio
- `symbols: List[str]` - List of symbols traded
- `initial_balance: float` - Starting balance
- `final_balance: float` - Ending balance
- `trades: List[TradeRecord]` - All trade records
- `equity_curve: pd.Series` - Equity over time
- `asset_results: Dict[str, AssetBacktestResult]` - Per-symbol results

#### Methods

##### `get_portfolio_summary() -> Dict`

Returns portfolio-level summary metrics.

**Returns:**
```python
{
    'portfolio_name': str,
    'symbols': List[str],
    'initial_balance': float,
    'final_balance': float,
    'total_return': float,  # Dollar return
    'total_return_pct': float,  # Percentage return
    'total_trades': int,
    'max_drawdown_pct': float,
    'win_rate': float,  # Percentage
    'profit_factor': float,
    'sharpe_ratio': float
}
```

##### `get_asset_contributions() -> Dict[str, Dict]`

Returns each asset's contribution to portfolio performance.

**Returns:**
```python
{
    'EURUSD': {
        'symbol': 'EURUSD',
        'total_return': float,
        'contribution_pct': float,  # % of total portfolio return
        'total_trades': int,
        'sharpe_ratio': float
    },
    # ... per symbol
}
```

##### `get_correlation_matrix() -> pd.DataFrame`

Calculates correlation matrix of trade returns across symbols.

**Returns:**
- DataFrame with correlations between symbol returns
- Empty DataFrame if insufficient data

**Example:**
```python
corr_matrix = result.get_correlation_matrix()
print(corr_matrix)

#           EURUSD  GBPUSD  USDJPY
# EURUSD     1.00    0.75   -0.15
# GBPUSD     0.75    1.00   -0.20
# USDJPY    -0.15   -0.20    1.00
```

---

### AssetBacktestResult

Per-asset backtest result (returned in `PortfolioBacktestResult.asset_results`).

#### Attributes

- `symbol: str` - Symbol name
- `total_trades: int` - Number of trades
- `total_return: float` - Total return in dollars
- `total_return_pct: float` - Total return as percentage
- `max_drawdown_pct: float` - Maximum drawdown percentage
- `win_rate: float` - Win rate percentage
- `profit_factor: float` - Ratio of gross profit to gross loss
- `sharpe_ratio: float` - Risk-adjusted return metric
- `trades: List[TradeRecord]` - Trade records for this symbol

---

### DataSynchronizer

Utility class for synchronizing multi-symbol data.

#### Static Methods

##### `synchronize(data_dict: Dict[str, pd.DataFrame], method: Literal['ffill', 'drop', 'interpolate'] = 'ffill', handle_leading_nans: Literal['drop', 'fill'] = 'drop', handle_trailing_nans: Literal['drop', 'fill'] = 'drop') -> Dict[str, pd.DataFrame]`

Synchronizes data across multiple symbols to a common timeline.

**Parameters:**
- `data_dict`: Dictionary mapping symbol → DataFrame
- `method`: Method for handling missing bars within the period
  - `'ffill'`: Forward-fill (use last known value)
  - `'drop'`: Drop bars with any missing data
  - `'interpolate'`: Linearly interpolate missing values
- `handle_leading_nans`: How to handle NaNs at start of period ('drop' or 'fill')
- `handle_trailing_nans`: How to handle NaNs at end of period ('drop' or 'fill')

**Returns:**
- Dictionary with synchronized DataFrames (all same length, same index)

**Example:**
```python
from apps.simulation.synchronizer import DataSynchronizer

# Original data with different lengths/timestamps
data = {
    'EURUSD': eurusd_df,  # 1000 bars
    'GBPUSD': gbpusd_df,  # 950 bars
    'USDJPY': usdjpy_df,  # 980 bars
}

# Synchronize with forward-fill
synced_data = DataSynchronizer.synchronize(
    data,
    method='ffill',
    handle_leading_nans='drop',
    handle_trailing_nans='drop'
)

# All DataFrames now have same index
assert len(set(len(df) for df in synced_data.values())) == 1
```

##### `validate_synchronized_data(data_dict: Dict[str, pd.DataFrame]) -> bool`

Validates that data is synchronized (all same index).

**Returns:**
- `True` if synchronized, `False` otherwise

##### `get_overlap_period(data_dict: Dict[str, pd.DataFrame]) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]`

Gets common time period across all DataFrames.

**Returns:**
- Tuple of (start_timestamp, end_timestamp) or (None, None) if no overlap

##### `trim_to_overlap(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]`

Trims all DataFrames to common overlap period.

**Returns:**
- Dictionary with trimmed DataFrames

---

## Allocation Methods

### Equal Weight

Allocates capital equally across all instruments (1/N per symbol).

```python
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'
)

# For 3 symbols: each gets 33.3% allocation
allocations = portfolio_strategy.calculate_allocations()
# Returns: {'EURUSD': 0.333, 'GBPUSD': 0.333, 'USDJPY': 0.333}
```

**Pros:**
- Simple and transparent
- No assumptions about volatility or correlations
- Works well for similar asset types

**Cons:**
- Doesn't account for different risk levels
- Can overweight high-volatility instruments

**Best for:**
- Similar instruments (e.g., all forex pairs)
- When you want simple diversification

---

### Risk Parity

Allocates capital inversely proportional to volatility (more capital to less volatile assets).

```python
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='risk_parity'
)

# Calculates volatility from data, allocates inversely
allocations = portfolio_strategy.calculate_allocations()
# Returns: {'EURUSD': 0.4, 'GBPUSD': 0.35, 'USDJPY': 0.25}  # Example
```

**How it works:**
1. Calculate return volatility for each symbol: `vol = returns.std()`
2. Calculate inverse volatilities: `inv_vol = 1 / vol`
3. Normalize to sum to 1.0: `allocation = inv_vol / sum(inv_vols)`

**Pros:**
- Risk-balanced portfolio
- Reduces impact of high-volatility instruments
- Better risk-adjusted returns

**Cons:**
- More complex
- Requires sufficient historical data
- Volatility can change over time

**Best for:**
- Mixed asset classes (forex, indices, commodities)
- When instruments have different volatility profiles

---

## Data Synchronization

### Why Synchronization Matters

When backtesting multiple symbols, data may have:
- Different numbers of bars
- Different timestamps (gaps, different sessions)
- Missing data for certain periods

Synchronization ensures all symbols are processed on the same timeline.

### Synchronization Methods

#### Forward-Fill (ffill) - Default

```python
result = engine.run(synchronize_data=True, sync_method='ffill')
```

**Behavior:**
- Creates union of all timestamps
- For missing bars, uses last known value
- Most common method for backtesting

**Example:**
```
EURUSD:  [1.10, 1.11, NaN,  1.12]
GBPUSD:  [1.30, NaN,  1.31, 1.32]
         ↓ (after ffill)
EURUSD:  [1.10, 1.11, 1.11, 1.12]  # NaN filled with 1.11
GBPUSD:  [1.30, 1.30, 1.31, 1.32]  # NaN filled with 1.30
```

**Pros:** Realistic (assumes price unchanged), no data loss
**Cons:** Can create false signals if gaps are large

---

#### Drop

```python
result = engine.run(synchronize_data=True, sync_method='drop')
```

**Behavior:**
- Drops any bar where any symbol has missing data
- Results in shorter backtest period

**Example:**
```
EURUSD:  [1.10, 1.11, NaN,  1.12]
GBPUSD:  [1.30, NaN,  1.31, 1.32]
         ↓ (after drop)
EURUSD:  [1.10,            1.12]  # Bars 1-2 dropped (GBPUSD/EURUSD had NaN)
GBPUSD:  [1.30,            1.32]
```

**Pros:** No synthetic data, conservative
**Cons:** Loses data, shorter backtest period

---

#### Interpolate

```python
result = engine.run(synchronize_data=True, sync_method='interpolate')
```

**Behavior:**
- Linearly interpolates missing values
- Uses surrounding values to estimate

**Example:**
```
EURUSD:  [1.10, 1.11, NaN,  1.13]
         ↓ (after interpolate)
EURUSD:  [1.10, 1.11, 1.12, 1.13]  # NaN interpolated as (1.11 + 1.13) / 2
```

**Pros:** Smooth data, full backtest period
**Cons:** Creates artificial data, can distort signals

---

### Leading/Trailing NaN Handling

```python
synced_data = DataSynchronizer.synchronize(
    data,
    method='ffill',
    handle_leading_nans='drop',   # Drop bars at start with NaNs
    handle_trailing_nans='drop'   # Drop bars at end with NaNs
)
```

**Options:**
- `'drop'`: Remove bars with NaNs (default, recommended)
- `'fill'`: Forward-fill (leading) or backward-fill (trailing)

---

## Performance Considerations

### Speed

**Expected Performance:**
- **N symbols ≈ N× time** (linear scaling)
- 1 symbol, 5000 bars: ~30s
- 3 symbols, 5000 bars: ~90s
- 5 symbols, 5000 bars: ~150s

**Why:**
- Bar-by-bar processing across all symbols
- Single-threaded execution
- Trade simulation overhead

**Mitigation:**
- Use vectorized mode (future enhancement)
- Reduce data size (shorter backtest period)
- Optimize strategies (minimize indicator calculations)

---

### Memory

**Memory Usage:**
- Scales linearly with number of symbols
- ~10-50 MB per symbol for 5000 bars

**For 10 symbols × 10000 bars:**
- Expected: ~300-500 MB total
- Memory overhead: 30-50 MB per symbol

**Tips:**
- Stream data if needed (load on-demand)
- Clear unused DataFrames after synchronization
- Use smaller timeframes only when necessary

---

## Best Practices

### 1. Symbol Selection

✅ **Do:**
- Choose low-correlated instruments (correlation < 0.5)
- Mix different asset classes (forex, indices, commodities)
- Verify sufficient liquidity for all symbols

❌ **Don't:**
- Trade highly correlated pairs (EURUSD + GBPUSD have ~0.7-0.9 correlation)
- Mix symbols with vastly different volatilities without risk parity
- Use too many symbols (5-10 is optimal)

**Check correlation:**
```python
result = engine.run()
corr_matrix = result.get_correlation_matrix()
print(corr_matrix)

# Look for correlations < 0.5 for good diversification
```

---

### 2. Data Quality

✅ **Do:**
- Verify data completeness before backtesting
- Use consistent timeframes across symbols
- Check for gaps and handle appropriately

```python
# Validate data before running
from apps.simulation.synchronizer import DataSynchronizer

start, end = DataSynchronizer.get_overlap_period(data)
print(f"Common period: {start} to {end}")

for symbol, df in data.items():
    print(f"{symbol}: {len(df)} bars, {df.isnull().sum().sum()} NaNs")
```

---

### 3. Capital Allocation

✅ **Do:**
- Start with equal_weight for similar instruments
- Use risk_parity for mixed volatility profiles
- Set max_total_exposure < 1.0 to reserve capital

```python
# Conservative allocation
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    max_total_exposure=0.8,  # Use only 80% of capital
    allocation_method='risk_parity'
)
```

---

### 4. Risk Management

✅ **Do:**
- Monitor portfolio-level drawdown
- Set stop-losses at strategy level
- Review correlation matrix regularly
- Limit exposure to correlated assets

```python
# Portfolio with correlation limits
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    max_correlated_exposure=0.5  # Max 50% in correlated assets
)

# Check results
summary = result.get_portfolio_summary()
if summary['max_drawdown_pct'] > 20:
    print("WARNING: Drawdown exceeds threshold")
```

---

### 5. Testing

✅ **Do:**
- Run integration tests on portfolio code
- Benchmark performance (speed and memory)
- Test with real MT5 data
- Verify results against single-symbol backtests

```python
# Compare portfolio vs individual
portfolio_result = portfolio_engine.run()
eurusd_only_result = single_engine.run(symbol='EURUSD')

# Portfolio should include EURUSD trades
eurusd_trades_from_portfolio = [
    t for t in portfolio_result.trades if t.symbol == 'EURUSD'
]
assert len(eurusd_trades_from_portfolio) == len(eurusd_only_result.trades)
```

---

## Examples

### Example 1: Basic Multi-Asset Portfolio

```python
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy

# Load data
data = {
    'EURUSD': eurusd_df,
    'GBPUSD': gbpusd_df,
    'USDJPY': usdjpy_df,
}

# Create symbol specs
symbol_specs = {
    symbol: SymbolInfoSimulator.from_mt5_symbol(symbol)
    for symbol in data.keys()
}

# Create strategies
strategies = {
    symbol: TrendFollowingStrategy(params={'symbol': symbol})
    for symbol in data.keys()
}

# Build portfolio
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'
)

# Run backtest
engine = PortfolioEngine(portfolio_strategy, initial_balance=30000)
result = engine.run(synchronize_data=True)

# Results
print(f"Total Return: {result.get_portfolio_summary()['total_return_pct']:.2f}%")
```

---

### Example 2: Risk Parity Allocation

```python
# Portfolio with risk-adjusted allocations
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='risk_parity'  # Inverse volatility weighting
)

# Check allocations
allocations = portfolio_strategy.calculate_allocations()
print("Allocations:")
for symbol, weight in allocations.items():
    print(f"  {symbol}: {weight*100:.1f}%")

# Run backtest
engine = PortfolioEngine(portfolio_strategy, initial_balance=50000)
result = engine.run()
```

---

### Example 3: Correlation Analysis

```python
# Run portfolio backtest
result = engine.run()

# Get correlation matrix
corr_matrix = result.get_correlation_matrix()
print("\nCorrelation Matrix:")
print(corr_matrix)

# Calculate average correlation
import numpy as np
mask = np.ones(corr_matrix.shape, dtype=bool)
np.fill_diagonal(mask, False)
avg_corr = corr_matrix.values[mask].mean()

print(f"\nAverage Correlation: {avg_corr:.3f}")
if avg_corr < 0.3:
    print("✓ Good diversification")
elif avg_corr < 0.6:
    print("⚠ Moderate diversification")
else:
    print("✗ Poor diversification")
```

---

### Example 4: Asset Contributions

```python
# Run backtest
result = engine.run()

# Get asset contributions
contributions = result.get_asset_contributions()

print("\nAsset Contributions:")
for symbol, contrib in contributions.items():
    print(f"\n{symbol}:")
    print(f"  Contribution: {contrib['contribution_pct']:.1f}%")
    print(f"  Total Return: ${contrib['total_return']:,.2f}")
    print(f"  Trades: {contrib['total_trades']}")
    print(f"  Sharpe Ratio: {contrib['sharpe_ratio']:.2f}")
```

---

### Example 5: Custom Symbol Specs

```python
# Create custom symbol specs (not from MT5)
from apps.simulation.data import SymbolInfoSimulator

symbol_specs = {
    'CUSTOM1': SymbolInfoSimulator(
        symbol='CUSTOM1',
        point=0.0001,
        contract_size=100000,
        digits=5,
        trade_tick_value=1.0,
        trade_tick_size=0.0001,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        currency_profit='USD',
        currency_base='EUR',
        currency_margin='EUR'
    ),
    # ... more symbols
}

# Use in portfolio
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'
)
```

---

## Troubleshooting

### Issue: "Strategy symbols don't match symbol spec symbols"

**Cause:** Symbol sets across strategies, symbol_specs, and data don't match.

**Fix:**
```python
# Ensure all three use the same symbols
symbols = ['EURUSD', 'GBPUSD', 'USDJPY']

strategies = {symbol: Strategy() for symbol in symbols}
symbol_specs = {symbol: SymbolInfoSimulator.from_mt5_symbol(symbol) for symbol in symbols}
data = {symbol: load_data(symbol) for symbol in symbols}
```

---

### Issue: "Data for EURUSD must have DatetimeIndex"

**Cause:** DataFrame index is not DatetimeIndex.

**Fix:**
```python
# Convert index to datetime
df.index = pd.to_datetime(df.index)

# Or set datetime column as index
df = df.set_index('timestamp')
```

---

### Issue: Backtest is very slow

**Causes:**
- Too many symbols (> 10)
- Large dataset (> 10000 bars)
- Complex strategies with many indicators

**Fixes:**
- Reduce number of symbols
- Use shorter backtest period
- Optimize strategy code
- Use coarser timeframe (H4 instead of M5)

---

### Issue: High correlation between symbols

**Cause:** Trading correlated instruments (EURUSD + GBPUSD).

**Fix:**
- Choose low-correlated pairs
- Limit max_correlated_exposure
- Use correlation matrix to identify issues

```python
# Check correlation before backtesting
returns_df = pd.DataFrame({
    symbol: data[symbol]['close'].pct_change()
    for symbol in symbols
})
corr = returns_df.corr()
print(corr)

# Replace high-correlation symbols
```

---

## Advanced Topics

### Custom Allocation Logic

```python
class CustomPortfolioStrategy(PortfolioStrategy):
    def calculate_allocations(self) -> Dict[str, float]:
        # Custom logic: allocate based on recent performance
        allocations = {}
        for symbol, data in self.data.items():
            recent_return = data['close'].pct_change(20).iloc[-1]
            allocations[symbol] = max(0.1, min(0.5, recent_return * 10))

        # Normalize
        total = sum(allocations.values())
        return {k: v/total for k, v in allocations.items()}
```

---

### Rebalancing

```python
# Manual rebalancing workflow
for period in rebalance_periods:
    # Recalculate allocations
    allocations = portfolio_strategy.calculate_allocations()

    # Update position sizes
    for symbol, target_alloc in allocations.items():
        current_size = get_current_position_size(symbol)
        target_size = calculate_target_size(target_alloc)
        if abs(current_size - target_size) > threshold:
            adjust_position(symbol, target_size)
```

---

## See Also

- [Simulation Module Documentation](simulation.md)
- [Strategy Development Guide](strategy_development.md)
- [API Reference](api_reference.md)
- [Examples Directory](../tests/usage/backtest/)

---

## Changelog

**2026-02-06**: Initial portfolio backtesting documentation
- Added PortfolioStrategy, PortfolioEngine, DataSynchronizer API docs
- Documented equal_weight and risk_parity allocation methods
- Added data synchronization guide
- Included performance benchmarks and best practices
- Added troubleshooting section
