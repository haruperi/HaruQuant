# Indicator Module

A comprehensive library of technical indicators for financial market analysis, providing trend, momentum, volatility, and volume indicators with a clean, consistent API.

## Overview

The `indicator` module provides a collection of commonly used technical indicators for analyzing price data. All indicators follow a consistent interface: they accept a pandas DataFrame with OHLCV data and return a new DataFrame with the indicator values added as additional columns.

## Key Features

- **Consistent API**: All indicators follow the same input/output pattern
- **Non-Destructive**: Original data is preserved; indicators add new columns
- **Pandas Integration**: Works seamlessly with pandas DataFrames
- **Type-Safe**: Full type hints for better IDE support
- **Logging**: Built-in logging for debugging and monitoring
- **Validation**: Input validation with clear error messages
- **Four Categories**: Trend, Momentum, Volatility, and Volume indicators

## Architecture

The module is organized into four categories of technical indicators:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   Trend          â”‚  â† SMA, EMA, WMA
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   Momentum       â”‚  â† RSI
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   Volatility     â”‚  â† ATR, Bollinger Bands
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   Volume         â”‚  â† Accumulation/Distribution
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 1. Trend Indicators

Trend indicators help identify the direction and strength of price movements over time.

### Functions

- **`sma()`** - Simple Moving Average
- **`ema()`** - Exponential Moving Average
- **`wma()`** - Weighted Moving Average

### Simple Moving Average (SMA)

Compute the simple moving average over a fixed window with equal weights.

**Function Signature:**
```python
sma(data: pd.DataFrame, window: int, price_col: str = "close") -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data
- `window: int` - Lookback period for averaging
- `price_col: str = "close"` - Column name for prices (default: "close")

**Returns:**
- `pd.DataFrame` - DataFrame with added column `sma_{window}`

**Description:**
SMA smooths price data by averaging the last `window` observations with equal weights. It filters noise, defines trend direction, and generates crossover signals when paired with other moving averages.

**Example:**
```python
from services.indicator import sma
import pandas as pd

# Sample data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
})

# Calculate 5-period SMA
result = sma(data, window=5)
print(result[['close', 'sma_5']])

# Calculate multiple SMAs
result = sma(result, window=10)
result = sma(result, window=20, price_col='close')
```

### Exponential Moving Average (EMA)

Compute the exponential moving average with exponentially decaying weights.

**Function Signature:**
```python
ema(data: pd.DataFrame, span: int, price_col: str = "close", adjust: bool = False) -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data
- `span: int` - Span for exponential weighting
- `price_col: str = "close"` - Column name for prices (default: "close")
- `adjust: bool = False` - Whether to use adjusted weights (default: False)

**Returns:**
- `pd.DataFrame` - DataFrame with added column `ema_{span}`

**Description:**
EMA smooths price data using exponentially decaying weights so recent values influence the average more than older ones. Compared to SMA, EMA reacts faster to price changes, making it popular for crossover systems and dynamic support/resistance.

**Example:**
```python
from services.indicator import ema
import pandas as pd

# Sample data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
})

# Calculate 12-period EMA
result = ema(data, span=12)
print(result[['close', 'ema_12']])

# Calculate multiple EMAs for crossover strategy
result = ema(result, span=26)
result['signal'] = result['ema_12'] > result['ema_26']
```

### Weighted Moving Average (WMA)

Compute the weighted moving average with linearly increasing weights.

**Function Signature:**
```python
wma(data: pd.DataFrame, window: int, price_col: str = "close") -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data
- `window: int` - Lookback period for averaging
- `price_col: str = "close"` - Column name for prices (default: "close")

**Returns:**
- `pd.DataFrame` - DataFrame with added column `wma_{window}`

**Description:**
WMA assigns linearly increasing weights to recent prices, giving more importance to recent data while still considering older values. It provides a middle ground between SMA and EMA in terms of responsiveness.

**Example:**
```python
from services.indicator import wma
import pandas as pd

# Sample data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
})

# Calculate 10-period WMA
result = wma(data, window=10)
print(result[['close', 'wma_10']])
```

### Trend Indicators Example

**Complete Trend Analysis:**

```python
from services.indicator import sma, ema, wma
import pandas as pd

# Load your data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112]
})

# Calculate multiple trend indicators
result = sma(data, window=5)
result = sma(result, window=10)
result = ema(result, span=12)
result = ema(result, span=26)
result = wma(result, window=10)

# Identify trend
result['uptrend'] = result['ema_12'] > result['ema_26']
result['strong_uptrend'] = (result['close'] > result['sma_5']) & (result['sma_5'] > result['sma_10'])

print(result[['close', 'sma_5', 'sma_10', 'ema_12', 'ema_26', 'uptrend']])
```

---

## 2. Momentum Indicators

Momentum indicators measure the rate of change in price movements to identify overbought or oversold conditions.

### Functions

- **`rsi()`** - Relative Strength Index

### Relative Strength Index (RSI)

Compute the RSI momentum oscillator to identify overbought/oversold conditions.

**Function Signature:**
```python
rsi(data: pd.DataFrame, period: int = 14, price_col: str = "close") -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data
- `period: int = 14` - Lookback period for smoothing (default: 14)
- `price_col: str = "close"` - Column name for prices (default: "close")

**Returns:**
- `pd.DataFrame` - DataFrame with added column `rsi_{period}`

**Description:**
RSI compares the magnitude of recent gains to recent losses over a fixed lookback to gauge the speed and change of price movements. Values oscillate between 0 and 100, where readings above 70 often signal overbought conditions and readings below 30 often signal oversold conditions.

**Calculation Steps:**
1. Compute price changes
2. Separate positive (gains) and negative (losses) moves
3. Smooth gains and losses with EWMA using alpha=1/period
4. Compute RS = avg_gain / avg_loss
5. Convert to RSI = 100 - 100/(1 + RS)

**Example:**
```python
from services.indicator import rsi
import pandas as pd

# Sample data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113]
})

# Calculate 14-period RSI
result = rsi(data, period=14)
print(result[['close', 'rsi_14']])

# Identify overbought/oversold
result['overbought'] = result['rsi_14'] > 70
result['oversold'] = result['rsi_14'] < 30

print(result[['close', 'rsi_14', 'overbought', 'oversold']])
```

**RSI Trading Signals:**

```python
from services.indicator import rsi
import pandas as pd

# Load your data
data = pd.DataFrame({
    'close': [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
})

# Calculate RSI
result = rsi(data, period=14)

# Generate trading signals
result['buy_signal'] = (result['rsi_14'] < 30) & (result['rsi_14'].shift(1) >= 30)
result['sell_signal'] = (result['rsi_14'] > 70) & (result['rsi_14'].shift(1) <= 70)

# Divergence detection
result['price_higher'] = result['close'] > result['close'].shift(5)
result['rsi_lower'] = result['rsi_14'] < result['rsi_14'].shift(5)
result['bearish_divergence'] = result['price_higher'] & result['rsi_lower']

print(result[['close', 'rsi_14', 'buy_signal', 'sell_signal']])
```

---

## 3. Volatility Indicators

Volatility indicators measure the degree of price variation to assess market risk and potential breakouts.

### Functions

- **`atr()`** - Average True Range
- **`bbands()`** - Bollinger Bands

### Average True Range (ATR)

Calculate the ATR volatility measure accounting for price gaps.

**Function Signature:**
```python
atr(data: pd.DataFrame, period: int = 14) -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data (requires 'high', 'low', 'close')
- `period: int = 14` - Lookback period (default: 14)

**Returns:**
- `pd.DataFrame` - DataFrame with added column `atr_{period}`

**Description:**
ATR captures the average range of price movement by taking the greatest of:
- Current high minus current low
- Absolute high minus previous close
- Absolute low minus previous close

Those true range values are then exponentially smoothed over `period` bars. Higher ATR indicates higher volatility.

**Example:**
```python
from services.indicator import atr
import pandas as pd

# Sample data
data = pd.DataFrame({
    'high': [102, 104, 103, 105, 107, 106, 108, 110, 109, 111],
    'low': [98, 100, 99, 101, 103, 102, 104, 106, 105, 107],
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
})

# Calculate 14-period ATR
result = atr(data, period=14)
print(result[['close', 'atr_14']])

# Use ATR for position sizing
result['position_size'] = 1000 / result['atr_14']  # Risk-based sizing
```

**ATR for Stop Loss:**

```python
from services.indicator import atr
import pandas as pd

# Load your data
data = pd.DataFrame({
    'high': [102, 104, 103, 105, 107],
    'low': [98, 100, 99, 101, 103],
    'close': [100, 102, 101, 103, 105]
})

# Calculate ATR
result = atr(data, period=14)

# Set stop loss at 2x ATR
result['stop_loss_long'] = result['close'] - (2 * result['atr_14'])
result['stop_loss_short'] = result['close'] + (2 * result['atr_14'])

print(result[['close', 'atr_14', 'stop_loss_long', 'stop_loss_short']])
```

### Bollinger Bands

Calculate Bollinger Bands for volatility-based trading ranges.

**Function Signature:**
```python
bbands(data: pd.DataFrame, period: int = 20, std_dev: float = 2.0, price_col: str = "close") -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data
- `period: int = 20` - Lookback period for moving average (default: 20)
- `std_dev: float = 2.0` - Number of standard deviations for bands (default: 2.0)
- `price_col: str = "close"` - Column name for prices (default: "close")

**Returns:**
- `pd.DataFrame` - DataFrame with added columns:
  - `bb_middle_{period}` - Middle band (SMA)
  - `bb_upper_{period}` - Upper band (SMA + std_dev * std)
  - `bb_lower_{period}` - Lower band (SMA - std_dev * std)
  - `bb_width_{period}` - Band width (upper - lower)

**Description:**
Bollinger Bands consist of a middle band (SMA) and two outer bands set at a specified number of standard deviations away. They expand during volatile periods and contract during quiet periods.

**Example:**
```python
from services.indicator.volatility import bbands
import pandas as pd

# Sample data
data = pd.DataFrame({
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112]
})

# Calculate Bollinger Bands
result = bbands(data, period=20, std_dev=2.0)
print(result[['close', 'bb_lower_20', 'bb_middle_20', 'bb_upper_20', 'bb_width_20']])

# Identify squeeze and expansion
result['squeeze'] = result['bb_width_20'] < result['bb_width_20'].rolling(20).mean()
result['expansion'] = result['bb_width_20'] > result['bb_width_20'].rolling(20).mean()
```

---

## 4. Volume Indicators

Volume indicators analyze trading volume to confirm price movements and identify potential reversals.

### Functions

- **`accumulation_distribution()`** - Accumulation/Distribution Line

### Accumulation/Distribution Line

Calculate the A/D line to measure cumulative money flow.

**Function Signature:**
```python
accumulation_distribution(data: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `data: pd.DataFrame` - DataFrame containing OHLCV data (requires 'high', 'low', 'close', 'volume')

**Returns:**
- `pd.DataFrame` - DataFrame with added column `ad_line`

**Description:**
The Accumulation/Distribution line is a volume-based indicator that measures the cumulative flow of money into and out of a security. It uses the relationship between price and volume to assess whether a security is being accumulated (bought) or distributed (sold).

**Calculation:**
1. Money Flow Multiplier = ((Close - Low) - (High - Close)) / (High - Low)
2. Money Flow Volume = Money Flow Multiplier Ã— Volume
3. A/D Line = Cumulative sum of Money Flow Volume

**Example:**
```python
from services.indicator import accumulation_distribution
import pandas as pd

# Sample data
data = pd.DataFrame({
    'high': [102, 104, 103, 105, 107, 106, 108, 110],
    'low': [98, 100, 99, 101, 103, 102, 104, 106],
    'close': [100, 102, 101, 103, 105, 104, 106, 108],
    'volume': [1000, 1200, 900, 1100, 1300, 1000, 1400, 1500]
})

# Calculate A/D Line
result = accumulation_distribution(data)
print(result[['close', 'volume', 'ad_line']])

# Identify divergence
result['price_trend'] = result['close'] > result['close'].shift(5)
result['ad_trend'] = result['ad_line'] > result['ad_line'].shift(5)
result['divergence'] = result['price_trend'] != result['ad_trend']
```

---

## Common Patterns

### Complete Technical Analysis

```python
from services.indicator import sma, ema, rsi, atr, accumulation_distribution
import pandas as pd

# Load your data
data = pd.DataFrame({
    'high': [102, 104, 103, 105, 107, 106, 108, 110, 109, 111],
    'low': [98, 100, 99, 101, 103, 102, 104, 106, 105, 107],
    'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
    'volume': [1000, 1200, 900, 1100, 1300, 1000, 1400, 1500, 1200, 1600]
})

# Calculate all indicators
result = sma(data, window=20)
result = ema(result, span=12)
result = ema(result, span=26)
result = rsi(result, period=14)
result = atr(result, period=14)
result = accumulation_distribution(result)

# Generate trading signals
result['trend_up'] = result['ema_12'] > result['ema_26']
result['not_overbought'] = result['rsi_14'] < 70
result['not_oversold'] = result['rsi_14'] > 30
result['buy_signal'] = result['trend_up'] & result['not_overbought']
result['sell_signal'] = ~result['trend_up'] & result['not_oversold']

print(result[['close', 'ema_12', 'ema_26', 'rsi_14', 'buy_signal', 'sell_signal']])
```

### Strategy Development

```python
from services.indicator import sma, rsi
import pandas as pd

def moving_average_crossover(data, fast=12, slow=26):
    """Simple moving average crossover strategy."""
    result = sma(data, window=fast)
    result = sma(result, window=slow)

    # Generate signals
    result['signal'] = 0
    result.loc[result[f'sma_{fast}'] > result[f'sma_{slow}'], 'signal'] = 1
    result.loc[result[f'sma_{fast}'] < result[f'sma_{slow}'], 'signal'] = -1

    # Detect crossovers
    result['position_change'] = result['signal'].diff()
    result['buy'] = result['position_change'] == 2
    result['sell'] = result['position_change'] == -2

    return result

def rsi_mean_reversion(data, period=14, oversold=30, overbought=70):
    """RSI mean reversion strategy."""
    result = rsi(data, period=period)

    # Generate signals
    result['buy'] = result[f'rsi_{period}'] < oversold
    result['sell'] = result[f'rsi_{period}'] > overbought
    result['exit'] = (result[f'rsi_{period}'] > 50) & (result[f'rsi_{period}'].shift(1) <= 50)

    return result

# Use the strategies
data = pd.DataFrame({'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]})
ma_strategy = moving_average_crossover(data)
rsi_strategy = rsi_mean_reversion(data)
```

### Combining Multiple Indicators

```python
from services.indicator import sma, ema, rsi, atr
import pandas as pd

def multi_indicator_filter(data):
    """Combine multiple indicators for robust signals."""
    # Calculate indicators
    result = sma(data, window=50)
    result = sma(result, window=200)
    result = ema(result, span=12)
    result = ema(result, span=26)
    result = rsi(result, period=14)
    result = atr(result, period=14)

    # Define conditions
    long_term_uptrend = result['close'] > result['sma_200']
    medium_term_uptrend = result['sma_50'] > result['sma_200']
    short_term_uptrend = result['ema_12'] > result['ema_26']
    not_overbought = result['rsi_14'] < 70
    sufficient_volatility = result['atr_14'] > result['atr_14'].rolling(20).mean()

    # Combine conditions
    result['strong_buy'] = (
        long_term_uptrend &
        medium_term_uptrend &
        short_term_uptrend &
        not_overbought &
        sufficient_volatility
    )

    return result

# Apply filter
data = pd.DataFrame({
    'high': [102, 104, 103, 105, 107],
    'low': [98, 100, 99, 101, 103],
    'close': [100, 102, 101, 103, 105]
})
filtered = multi_indicator_filter(data)
```

---

## Best Practices

1. **Use appropriate periods**: Choose indicator periods based on your trading timeframe
2. **Combine indicators**: Use multiple indicators from different categories for confirmation
3. **Avoid over-optimization**: Don't fit indicators too closely to historical data
4. **Consider market conditions**: Indicators perform differently in trending vs ranging markets
5. **Validate inputs**: Always check that required columns exist before calculation
6. **Handle missing data**: Be aware of NaN values in early periods
7. **Test thoroughly**: Backtest strategies before live trading
8. **Monitor performance**: Track indicator effectiveness over time
9. **Use consistent data**: Ensure OHLCV data is clean and properly formatted
10. **Document parameters**: Keep track of which indicator parameters work best

## Indicator Categories Summary

### Trend Indicators
- **Purpose**: Identify direction and strength of price movements
- **Best for**: Trending markets, crossover strategies
- **Examples**: SMA, EMA, WMA

### Momentum Indicators
- **Purpose**: Measure rate of price change
- **Best for**: Identifying overbought/oversold conditions
- **Examples**: RSI

### Volatility Indicators
- **Purpose**: Measure price variation and risk
- **Best for**: Position sizing, stop loss placement, breakout detection
- **Examples**: ATR, Bollinger Bands

### Volume Indicators
- **Purpose**: Confirm price movements with volume
- **Best for**: Validating trends, spotting divergences
- **Examples**: Accumulation/Distribution

## Common Indicator Combinations

**Trend Following:**
- SMA(50) + SMA(200) for long-term trend
- EMA(12) + EMA(26) for short-term signals

**Mean Reversion:**
- RSI(14) for overbought/oversold
- Bollinger Bands for price extremes

**Breakout Trading:**
- ATR for volatility measurement
- Bollinger Bands for squeeze detection

**Confirmation:**
- Price trend + A/D Line for volume confirmation
- Multiple timeframe analysis

## License

Copyright 2025, HaruQuant

## See Also

- `services/strategy/` - Strategy framework for backtesting
- `apps/trading/` - Trading execution module
- `services/data/mt5.py` - MT5 data integration

