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
from typing import Optional, Dict, Any
import pandas as pd
from services.indicator import ema
from apps.logger import logger
from services.strategy import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    """
    EMA Crossover Trend Following Strategy

    Classic trend following approach using two EMAs to identify trend direction.
    Exit signals are based on EMA crossovers.

    This strategy:
    - Follows the trend using EMA crossovers

    Parameters (via params dict):
        ema_fast: Fast EMA period (default: 20)
        ema_slow: Slow EMA period (default: 50)
        ema_filter: Filter EMA period (default: 200)
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize trend following strategy.
        """
        super().__init__(params)

        # Extract parameters with defaults
        self.fast_period = self.params.get('fast_period', 20)
        self.slow_period = self.params.get('slow_period', 50)
        self.filter_period = self.params.get('filter_period', 200)

    def on_init(self) -> None:
        """Initialize strategy."""
        logger.info(f"MA Crossover Strategy initialized for {self.params['symbol']}")
        logger.info(f"Parameters: Fast={self.fast_period}, Slow={self.slow_period}, Filter={self.filter_period}")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators and detect EMA crossovers.

        Logic:
        1. Calculate 3 EMAs (Fast, Slow, Filter)
        2. Shift them by 1 to use previous bar values (simulating live trading)
        3. Define conditions:
           - Condition 1: Fast EMA > Slow EMA (Trend)
           - Condition 2: Prev Fast EMA < Prev Slow EMA (Crossover)
           - Condition 3: Slow EMA > Filter EMA (Filter)
        4. Generate signals:
           - Buy: Cond 1 & Cond 2 & Cond 3
           - Sell: Inverse of above
           - Exit Buy (Close Sell): Cond 1 & Cond 2 (Crossover Up)
           - Exit Sell (Close Buy): Inverse of above (Crossover Down)
        """
        # Calculate indicators
        data = ema(data, self.fast_period)
        data = ema(data, self.slow_period)
        data = ema(data, self.filter_period)

        # Get column names
        ema_fast_col = f'ema_{self.fast_period}'
        ema_slow_col = f'ema_{self.slow_period}'
        ema_filter_col = f'ema_{self.filter_period}'

        # Shift indicators to use previous bar values
        data[ema_fast_col] = data[ema_fast_col].shift(1)
        data[ema_slow_col] = data[ema_slow_col].shift(1)
        data[ema_filter_col] = data[ema_filter_col].shift(1)

        # Creating prev columns (which are now shift(2) relative to original data)
        data[f'prev_{ema_fast_col}'] = data[ema_fast_col].shift(1)
        data[f'prev_{ema_slow_col}'] = data[ema_slow_col].shift(1)

        # Initialize signal columns
        # Initialize signal columns
        data['entry_signal'] = 0
        data['exit_signal'] = 0
        data['pending_signal'] = 0
        data['cancel_pending_signal'] = 0
        data['price'] = float('nan')

        # Define Conditions
        # Condition 1: Fast > Slow (Current State)
        condition_1_buy = data[ema_fast_col] > data[ema_slow_col]
        condition_1_sell = data[ema_fast_col] < data[ema_slow_col]

        # Condition 2: Prev Fast < Prev Slow (Crossover State)
        condition_2_buy = data[f'prev_{ema_fast_col}'] < data[f'prev_{ema_slow_col}']
        condition_2_sell = data[f'prev_{ema_fast_col}'] > data[f'prev_{ema_slow_col}']

        # Condition 3: Filter (Slow > Filter)
        condition_3_buy = data[ema_slow_col] > data[ema_filter_col]
        condition_3_sell = data[ema_slow_col] < data[ema_filter_col]

        # Generate Signals

        # Exit Signals first (Cross in opposite direction)
        # Bullish Cross (Exit Short)
        condition_exit_short = condition_1_buy & condition_2_buy
        data.loc[condition_exit_short, 'exit_signal'] = -1  # Exit Sell
        # Price is not strictly needed for exit as market order, but good for reference
        data.loc[condition_exit_short, 'price'] = data.loc[condition_exit_short, 'open']

        # Bearish Cross (Exit Long)
        condition_exit_long = condition_1_sell & condition_2_sell
        data.loc[condition_exit_long, 'exit_signal'] = 1   # Exit Buy
        data.loc[condition_exit_long, 'price'] = data.loc[condition_exit_long, 'open']

        # Entry Signals (overwrite exits if valid entry)
        # Buy Signal
        condition_entry_buy = condition_1_buy & condition_2_buy & condition_3_buy
        data.loc[condition_entry_buy, 'entry_signal'] = 1
        data.loc[condition_entry_buy, 'price'] = data.loc[condition_entry_buy, 'open']

        # Sell Signal
        condition_entry_sell = condition_1_sell & condition_2_sell & condition_3_sell
        data.loc[condition_entry_sell, 'entry_signal'] = -1
        data.loc[condition_entry_sell, 'price'] = data.loc[condition_entry_sell, 'open']

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
        """
        Get signal details for a specific bar.
        """
        row = data.iloc[index]
        entry = row['entry_signal']
        exit_sig = row['exit_signal']

        if entry == 0 and exit_sig == 0:
            return None

        # Get bar data
        bar = data.iloc[index]
        entry_price = bar["price"]

        # Variables init
        reason = None
        entry_signal = 0
        exit_signal = 0
        sl = None
        tp = None

        if entry == 1:
            reason = f"Fast({self.fast_period}) crossed above Slow({self.slow_period}) > Filter({self.filter_period})"
            entry_signal = 1
        elif entry == -1:
            reason = f"Fast({self.fast_period}) crossed below Slow({self.slow_period}) < Filter({self.filter_period})"
            entry_signal = -1

        if exit_sig == 1:
            reason = f"Close Buy: Bearish Crossover" if not reason else reason + " | Close Buy"
            exit_signal = 1
        elif exit_sig == -1:
            reason = f"Close Sell: Bullish Crossover" if not reason else reason + " | Close Sell"
            exit_signal = -1

        return {
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "time": bar.name,
            "reason": reason,
            "price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
        }
```

### Running a Strategy

```python
# Initialize
 strategy = TrendFollowingStrategy(
        params={
            'symbol': 'EURUSD',
            'fast_period': 20,
            'slow_period': 50,
            'filter_period': 200
        }
    )

strategy.on_init()

# Calculate indicators and signals
df_with_signals = strategy.on_bar(market_data_df)

# Check specific bar for signals
last_bar_idx = len(df_with_signals) - 1
signal = strategy.get_signal(df_with_signals, last_bar_idx)

if signal:
    print(f"Signal generated: {signal}")
```
