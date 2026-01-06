# Strategy Module

A simplified, DataFrame-based trading strategy framework for clean and intuitive strategy development.

## Overview

The **Strategy module** provides a clean, simple API for building trading strategies. Strategies calculate indicators, generate signals via a DataFrame column, and return signal details when requested.

## Core Principles

1. **Simplicity**: 4 methods instead of 10+
2. **DataFrame-Based**: Signals stored in DataFrame column
3. **Flexible**: Params dict allows any configuration
4. **Vectorized**: Calculate all indicators at once
5. **Testable**: Clear inputs and outputs

---

## Quick Start

```python
from apps.strategy import TrendFollowingStrategy
from apps.utils.data_getters import load_mt5

# Create strategy with params dict
strategy = TrendFollowingStrategy(
    symbol="EURUSD",
    params={
        'ema_fast': 20,
        'ema_slow': 50,
        'atr_period': 14,
        'atr_sl_multiplier': 2.0,
        'atr_tp_multiplier': 4.0
    }
)

# Initialize
strategy.on_init()

# Load data
data = load_mt5("EURUSD", timeframe="H1", start_date="2025-01-01")

# Calculate indicators and signals (vectorized - happens once)
data = strategy.on_bar(data)

# Iterate through signals
for i in range(len(data)):
    signal_info = strategy.get_signal(data, i)
    if signal_info:
        print(f"{signal_info['time']}: {signal_info['reason']}")
        print(f"  Entry: {signal_info['entry_price']:.5f}")
        print(f"  SL: {signal_info['stop_loss']:.5f}")
        print(f"  TP: {signal_info['take_profit']:.5f}")
```

---

## API Reference

### BaseStrategy

All strategies inherit from `BaseStrategy` and implement these methods:

#### Required Methods

```python
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate indicators and add 'signal' column.

    Signal values:
    - 1: Long signal
    - 0: No signal
    - -1: Short signal

    Returns:
        DataFrame with indicators and signal column added
    """
    pass
```

#### Optional Methods

```python
def on_init(self) -> None:
    """Initialize strategy (optional)."""
    pass

def on_tick(self, data: pd.DataFrame) -> pd.DataFrame:
    """Process tick data (optional, for live trading)."""
    pass

def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
    """
    Get signal details for a specific bar.

    Returns:
        dict with keys: signal, time, reason, stop_loss, take_profit
        or None if no signal at that index
    """
    pass
```

#### Helper Methods

```python
# Get indicator value safely (returns None for NaN)
value = self.get_indicator_value(data, 'ema_20', offset=0)

# Detect bullish crossover
if self.crossover(data['ema_20'], data['ema_50']):
    # EMA(20) just crossed above EMA(50)
    pass

# Detect bearish crossunder
if self.crossunder(data['ema_20'], data['ema_50']):
    # EMA(20) just crossed below EMA(50)
    pass
```

---

## Creating a Custom Strategy

### Minimal Example

```python
from apps.strategy import BaseStrategy
from apps.indicator import sma
import pandas as pd
from typing import Optional, Dict, Any

class SimpleMAStrategy(BaseStrategy):
    """Buy when price above SMA, sell when below"""

    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(symbol, params)
        self.ma_period = self.params.get('ma_period', 50)

    def on_init(self) -> None:
        print(f"SimpleMA initialized for {self.symbol}")
        print(f"Parameters: SMA({self.ma_period})")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        # Calculate indicator
        data = sma(data, self.ma_period)

        # Initialize signal column
        data['signal'] = 0

        # Generate signals
        for i in range(len(data)):
            close = data.iloc[i]['close']
            ma = data.iloc[i][f'sma_{self.ma_period}']

            if pd.isna(ma):
                continue

            if close > ma:
                data.loc[data.index[i], 'signal'] = 1  # Long
            elif close < ma:
                data.loc[data.index[i], 'signal'] = -1  # Short

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
        signal_value = data.iloc[index]['signal']

        if signal_value == 0:
            return None

        bar = data.iloc[index]

        return {
            'signal': int(signal_value),
            'time': bar.name,
            'reason': f"Price {'above' if signal_value == 1 else 'below'} SMA",
            'entry_price': bar['close']
        }
```

### Usage

```python
# Create strategy
strategy = SimpleMAStrategy("EURUSD", params={'ma_period': 50})

# Initialize
strategy.on_init()

# Process data
data = load_mt5("EURUSD", timeframe="H1", start_date="2025-01-01")
data = strategy.on_bar(data)

# Check signals
signals = data[data['signal'] != 0]
print(f"Found {len(signals)} signals")
```

---

## Built-in Strategies

### 1. TrendFollowingStrategy

EMA crossover strategy with ATR-based risk management.

**Entry**:
- LONG: EMA(fast) crosses above EMA(slow)
- SHORT: EMA(fast) crosses below EMA(slow)

**Risk Management**:
- SL: Entry ± (atr_sl_multiplier × ATR)
- TP: Entry ± (atr_tp_multiplier × ATR)

**Usage**:
```python
from apps.strategy import TrendFollowingStrategy

strategy = TrendFollowingStrategy(
    symbol="EURUSD",
    params={
        'ema_fast': 20,
        'ema_slow': 50,
        'atr_period': 14,
        'atr_sl_multiplier': 2.0,
        'atr_tp_multiplier': 4.0
    }
)
```

**Parameters**:
- `ema_fast`: Fast EMA period (default: 20)
- `ema_slow`: Slow EMA period (default: 50)
- `atr_period`: ATR period (default: 14)
- `atr_sl_multiplier`: SL distance in ATR multiples (default: 2.0)
- `atr_tp_multiplier`: TP distance in ATR multiples (default: 4.0)

### 2. MeanReversionStrategy

Bollinger Bands + RSI counter-trend strategy.

**Entry**:
- LONG: Price ≤ lower BB AND RSI < oversold
- SHORT: Price ≥ upper BB AND RSI > overbought

**Exit**:
- Price returns to middle BB

**Usage**:
```python
from apps.strategy import MeanReversionStrategy

strategy = MeanReversionStrategy(
    symbol="EURUSD",
    params={
        'bb_period': 20,
        'bb_std': 2.0,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
)
```

**Parameters**:
- `bb_period`: Bollinger Bands period (default: 20)
- `bb_std`: BB standard deviation (default: 2.0)
- `rsi_period`: RSI period (default: 14)
- `rsi_oversold`: Oversold threshold (default: 30)
- `rsi_overbought`: Overbought threshold (default: 70)

---

## Signal Column Approach

### Signal Values

Strategies add a `signal` column to the DataFrame:
- `1` = Long signal
- `0` = No signal
- `-1` = Short signal

### Accessing Signals

```python
# Filter to only bars with signals
signals_df = data[data['signal'] != 0]

# Separate long and short signals
long_signals = data[data['signal'] == 1]
short_signals = data[data['signal'] == -1]

# Count signals
total_signals = (data['signal'] != 0).sum()
long_count = (data['signal'] == 1).sum()
short_count = (data['signal'] == -1).sum()
```

### Signal Details

`get_signal()` returns a dict with:

```python
{
    'signal': 1,              # 1 (long), -1 (short)
    'time': Timestamp,        # When signal occurred
    'reason': str,            # Human-readable explanation
    'stop_loss': float,       # SL price (optional)
    'take_profit': float,     # TP price (optional)
    'entry_price': float,     # Entry price
    # ... strategy-specific fields
}
```

---

## Design Patterns

### Pattern 1: Crossover Detection

```python
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    # Calculate indicators
    data = ema(data, 20)
    data = ema(data, 50)

    # Initialize signal column
    data['signal'] = 0

    # Detect crossovers
    for i in range(1, len(data)):
        ema_fast = data['ema_20'].iloc[:i+1]
        ema_slow = data['ema_50'].iloc[:i+1]

        if self.crossover(ema_fast, ema_slow):
            data.loc[data.index[i], 'signal'] = 1
        elif self.crossunder(ema_fast, ema_slow):
            data.loc[data.index[i], 'signal'] = -1

    return data
```

### Pattern 2: Condition-Based Signals

```python
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    # Calculate indicators
    data = rsi(data, 14)
    data = bbands(data, 20, 2.0)

    # Initialize signal column
    data['signal'] = 0

    # Check conditions for each bar
    for i in range(len(data)):
        close = data.iloc[i]['close']
        rsi_val = data.iloc[i]['rsi_14']
        bb_lower = data.iloc[i]['bb_lower_20_2']
        bb_upper = data.iloc[i]['bb_upper_20_2']

        # Skip if indicators not ready
        if pd.isna(rsi_val) or pd.isna(bb_lower):
            continue

        # Oversold condition
        if close <= bb_lower and rsi_val < 30:
            data.loc[data.index[i], 'signal'] = 1

        # Overbought condition
        elif close >= bb_upper and rsi_val > 70:
            data.loc[data.index[i], 'signal'] = -1

    return data
```

### Pattern 3: Dynamic SL/TP

```python
def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
    signal_value = data.iloc[index]['signal']

    if signal_value == 0:
        return None

    bar = data.iloc[index]
    close = bar['close']
    atr = bar[f'atr_{self.atr_period}']

    # Calculate SL/TP based on ATR
    if signal_value == 1:  # Long
        sl = close - (self.sl_multiplier * atr)
        tp = close + (self.tp_multiplier * atr)
    else:  # Short
        sl = close + (self.sl_multiplier * atr)
        tp = close - (self.tp_multiplier * atr)

    return {
        'signal': int(signal_value),
        'time': bar.name,
        'reason': f"Signal at {close:.5f}",
        'stop_loss': sl,
        'take_profit': tp,
        'entry_price': close,
        'atr': atr
    }
```

---

## Testing Strategies

### Unit Testing

```python
import pandas as pd
from apps.strategy import TrendFollowingStrategy

def test_crossover_detection():
    # Create strategy
    strategy = TrendFollowingStrategy("EURUSD", params={
        'ema_fast': 20,
        'ema_slow': 50
    })

    # Create mock data with crossover
    data = pd.DataFrame({
        'open': [1.1000, 1.1010, 1.1020, 1.1030],
        'high': [1.1005, 1.1015, 1.1025, 1.1035],
        'low': [1.0995, 1.1005, 1.1015, 1.1025],
        'close': [1.1000, 1.1010, 1.1020, 1.1030],
        'volume': [100, 100, 100, 100]
    })

    # Process data
    data = strategy.on_bar(data)

    # Check signals
    signals = data[data['signal'] != 0]
    assert len(signals) > 0, "Should detect crossover"
```

### Determinism Testing

```python
def test_determinism():
    """Same data should produce same signals"""
    strategy1 = TrendFollowingStrategy("EURUSD")
    strategy2 = TrendFollowingStrategy("EURUSD")

    # Same data
    data = load_test_data()

    # Process with both strategies
    result1 = strategy1.on_bar(data.copy())
    result2 = strategy2.on_bar(data.copy())

    # Should be identical
    assert result1['signal'].equals(result2['signal'])
```

---

## Performance Considerations

### 1. Vectorized Operations

Indicators are calculated **once** on the entire DataFrame using vectorized pandas operations:

```python
# Good: Vectorized (fast)
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    data = ema(data, 20)  # Calculates for ALL bars at once
    data = ema(data, 50)
    return data

# Bad: Per-bar calculation (slow)
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    for i in range(len(data)):
        # Don't calculate indicators per bar!
        pass
```

### 2. Signal Detection Loop

The signal detection loop is necessary to check each bar's conditions:

```python
# This is fine - checking conditions per bar
for i in range(len(data)):
    if condition_met:
        data.loc[data.index[i], 'signal'] = 1
```

### 3. Efficient Lookups

Use `.iloc[]` for position-based indexing:

```python
# Good: Direct indexing
close = data.iloc[i]['close']

# Slower: Multiple lookups
close = data.loc[data.index[i], 'close']
```

---

## Common Patterns

### Accessing Previous Values

```python
# Current bar
current = data.iloc[-1]

# Previous bar
previous = data.iloc[-2]

# N bars ago
n_bars_ago = data.iloc[-n]
```

### Checking for NaN

```python
# Use helper method
value = self.get_indicator_value(data, 'ema_50')
if value is None:
    # Indicator not ready
    pass

# Or check directly
if pd.isna(data.iloc[i]['ema_50']):
    continue
```

### Crossover Detection

```python
# Get series up to current bar
for i in range(1, len(data)):
    fast = data['ema_20'].iloc[:i+1]
    slow = data['ema_50'].iloc[:i+1]

    if self.crossover(fast, slow):
        data.loc[data.index[i], 'signal'] = 1
```

---

## Examples

### Example 1: Simple Moving Average Crossover

```python
from apps.strategy import BaseStrategy
from apps.indicator import sma

class SMAStrategy(BaseStrategy):
    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(symbol, params)
        self.fast = self.params.get('fast', 10)
        self.slow = self.params.get('slow', 30)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = sma(data, self.fast)
        data = sma(data, self.slow)
        data['signal'] = 0

        for i in range(1, len(data)):
            if self.crossover(data[f'sma_{self.fast}'].iloc[:i+1],
                             data[f'sma_{self.slow}'].iloc[:i+1]):
                data.loc[data.index[i], 'signal'] = 1
            elif self.crossunder(data[f'sma_{self.fast}'].iloc[:i+1],
                                data[f'sma_{self.slow}'].iloc[:i+1]):
                data.loc[data.index[i], 'signal'] = -1

        return data
```

### Example 2: RSI Strategy

```python
from apps.strategy import BaseStrategy
from apps.indicator import rsi

class RSIStrategy(BaseStrategy):
    def __init__(self, symbol: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(symbol, params)
        self.period = self.params.get('period', 14)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = rsi(data, self.period)
        data['signal'] = 0

        for i in range(len(data)):
            rsi_val = data.iloc[i][f'rsi_{self.period}']

            if pd.isna(rsi_val):
                continue

            if rsi_val < self.oversold:
                data.loc[data.index[i], 'signal'] = 1  # Oversold - buy
            elif rsi_val > self.overbought:
                data.loc[data.index[i], 'signal'] = -1  # Overbought - sell

        return data
```

---

## FAQ

### Q: Why use params dict instead of individual parameters?

**A**: Flexibility! You can add/remove parameters without changing the method signature. It's also more consistent across strategies.

```python
# Flexible - easy to add new params
strategy = MyStrategy("EURUSD", params={
    'param1': 10,
    'param2': 20,
    'new_param': 30  # Easy to add
})
```

### Q: Why calculate signals in on_bar() instead of separate method?

**A**: Simplicity! Everything happens in one place. You calculate indicators and generate signals in the same method.

### Q: Can I access previous signals?

**A**: Yes! The signal column is in the DataFrame, so you can access any previous signal:

```python
# Get previous signal
prev_signal = data.iloc[i-1]['signal']

# Check if signal changed
if data.iloc[i]['signal'] != prev_signal:
    # Signal changed
    pass
```

### Q: How do I handle multiple timeframes?

**A**: Pass higher timeframe data via params:

```python
# Load both timeframes
h1_data = load_mt5("EURUSD", "H1")
h4_data = load_mt5("EURUSD", "H4")

# Pass H4 data as param
strategy = MyStrategy("EURUSD", params={
    'htf_data': h4_data
})

# Access in on_bar
def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
    htf_data = self.params.get('htf_data')
    # Use htf_data for trend filter
```

---

## Contributing

When creating new strategies:

1. Inherit from `BaseStrategy`
2. Use params dict for configuration
3. Implement `on_bar()` to calculate indicators and add signal column
4. Implement `get_signal()` to return signal details
5. Use `apps.indicator` for indicators
6. Test for determinism
7. Document parameters and logic

---

## License

Part of the HaruQuant trading framework.
