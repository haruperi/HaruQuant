# Strategy Module

This module provides the framework for developing, managing, and executing trading strategies.

## Files

### 1. `base.py`

**Purpose**
Defines the abstract base class and interface for all trading strategies. It enforces a standard lifecycle (`on_init`, `on_bar`, `on_tick`) and a standardized signal generation format (`entry_signal`, `exit_signal`, etc.).

**Classes**

*   **`SignalDict(TypedDict)`**: Dictionary structure for returning signal details (entry/exit signals, price, SL/TP, reason, time).

*   **`BaseStrategy(ABC)`**: Abstract base class for all strategies.
    *   `__init__(params: Optional[Dict[str, Any]] = None)`: Initialize strategy with parameters.
    *   `on_init() -> None`: Abstract method. Initialize strategy state (validate params, setup logs).
    *   `on_tick(data: pd.DataFrame) -> pd.DataFrame`: Optional method for tick-by-tick processing.
    *   `on_bar(data: pd.DataFrame) -> pd.DataFrame`: **Core Logic**. Abstract method. Calculates indicators and adds signal columns (`entry_signal`, `exit_signal`, etc.) to the DataFrame.
    *   `get_signal(data: pd.DataFrame, index: int) -> Optional[SignalDict]`: Extract signal details for a specific bar index.
    *   **Helper Methods**:
        *   `get_indicator_value(data: pd.DataFrame, column: str, offset: int = 0) -> Optional[float]`: Get indicator value safely.
        *   `crossover(series1: pd.Series, series2: pd.Series) -> bool`: Detect bullish crossover (series1 crosses above series2).
        *   `crossunder(series1: pd.Series, series2: pd.Series) -> bool`: Detect bearish crossunder (series1 crosses below series2).

### 2. `storage.py`

**Purpose**
Manages the file storage system for strategy code versioning. It handles saving, loading, listing versions, and export/import functionality for strategies.

**Classes**

*   **`StrategyStorage`**: Manager class for filesystem operations.
    *   `save_strategy(...) -> str`: Save strategy code and metadata to a versioned directory.
    *   `load_strategy_code(...) -> str`: Load raw strategy Python code from file.
    *   `load_strategy_class(...) -> Type[BaseStrategy]`: Dynamically load and return the Strategy class from a file.
    *   `load_strategy_metadata(...) -> Dict[str, Any]`: Load strategy metadata (params, author, etc.).
    *   `list_versions(...) -> List[str]`: List all available versions for a strategy.
    *   `delete_strategy(...) -> None`: Delete all versions of a strategy.
    *   `delete_strategy_version(...) -> None`: Delete a specific version.
    *   `export_strategy(...) -> str`: Export a strategy version to a ZIP file.
    *   `import_strategy(...) -> str`: Import a strategy from a ZIP file.

## Usage Examples

For a complete runnable example, see [`tests/usage/strategy/demo.py`](../../tests/usage/strategy/demo.py).

### Implementing a Strategy

```python
from apps.strategy.base import BaseStrategy
import pandas as pd
import pandas_ta as ta

class TrendFollowingStrategy(BaseStrategy):
    def on_init(self):
        # Validate parameters or setup defaults
        self.fasters = self.params.get('fast_period', 20)
        self.slowers = self.params.get('slow_period', 50)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        # 1. Calculate Indicators
        data['fast_ema'] = ta.ema(data['close'], length=self.fasters)
        data['slow_ema'] = ta.ema(data['close'], length=self.slowers)

        # 2. Generate Signals (Vectorized)
        data['entry_signal'] = 0
        data['exit_signal'] = 0

        # Buy when fast EMA crosses above slow EMA
        buy_signal = (data['fast_ema'] > data['slow_ema']) & (data['fast_ema'].shift(1) <= data['slow_ema'].shift(1))
        data.loc[buy_signal, 'entry_signal'] = 1

        # Sell/Exit when fast EMA crosses below
        sell_signal = (data['fast_ema'] < data['slow_ema']) & (data['fast_ema'].shift(1) >= data['slow_ema'].shift(1))
        data.loc[sell_signal, 'exit_signal'] = 1  # Or 'entry_signal' = -1 for short

        return data
```

### Running a Strategy

```python
# Initialize
strategy = TrendFollowingStrategy(params={'symbol': 'EURUSD', 'fast_period': 20, 'slow_period': 50})
strategy.on_init()

# Process Data
df_with_signals = strategy.on_bar(market_data_df)

# Check specific bar for signals
last_bar_idx = len(df_with_signals) - 1
signal = strategy.get_signal(df_with_signals, last_bar_idx)

if signal:
    print(f"Signal generated: {signal}")
```
