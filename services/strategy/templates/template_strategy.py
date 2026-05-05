"""
Template Strategy.

A clean starting point for creating new strategies.
 Implement your main logic in on_bar() and signal parsing in get_signal().

Entry Signals:
- Define your entry conditions in on_bar()
- Return signal details in get_signal()
"""

from typing import Any, Dict, Optional

import pandas as pd

from services.utils.logger import logger
from services.strategy import BaseStrategy
from services.strategy.base import SignalDict

# Import indicators as needed
# from services.indicator import atr, ema, rsi, sma


class TemplateStrategy(BaseStrategy):
    """
    [Strategy Name].

    [Brief Description of Strategy Logic]

    Entry Signals:
    - Long: [Condition]
    - Short: [Condition]

    Parameters (via params dict):
        symbol: Trading symbol (e.g., "EURUSD")
        timeframe: Timeframe (e.g., "H1", "D1")

        Add your custom parameters here:
        - param1: Description (default: value)
        - param2: Description (default: value)
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy parameters.

        Args:
            params: Strategy parameters dict with keys:
                - symbol: Trading symbol (required)
                - timeframe: Timeframe (required)
                - Add your custom parameters here

        Example:
            strategy = EmptyStrategy({
                'symbol': 'EURUSD',
                'timeframe': 'H1',
                'param1': value1,
                'param2': value2
            })
        """
        super().__init__(params)

        # Extract your custom parameters with defaults
        # self.param1 = self.params.get('param1', default_value)
        # self.param2 = self.params.get('param2', default_value)

        # Validate parameters if needed
        # if self.param1 <= 0:
        #     raise ValueError(f"param1 must be positive, got {self.param1}")

    def on_init(self) -> None:
        """
        Initialize strategy (called once at start).

        Use this to:
        - Log strategy parameters
        - Set up any initial state
        - Validate configuration
        """
        logger.info(f"TemplateStrategy initialized for {self.params['symbol']}")
        # Log your parameters here
        # logger.info(f"Parameters: param1={self.param1}, param2={self.param2}")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process each bar and generate trading signals.

        This method is called for every bar both in backtest and live trading.

        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)

        Returns:
            DataFrame with added indicator columns and 'signal' and 'price' columns

        Responsibilities:
        1. Calculate indicators
        2. Generate 'signal' column (calculate on open based on previous bar data)
        3. Generate 'price' column (usually the opening price of the bar is market price)

        Signal values (Integer columns):
         - entry_signal: 1 (Buy), -1 (Sell), 0 (None)
         - exit_signal: 1 (Exit Buy), -1 (Exit Sell), 0 (None)
         - pending_signal: 1 (Buy Stop), -1 (Sell Stop), 2 (Buy Limit), -2 (Sell Limit)
         - cancel_pending_signal: 1 (Cancel Entry), 2 (Cancel Exit) - implementation defined
         - price: Price level for entry/pending

        """
        # TODO: 1. Calculate your indicators here
        # data = sma(data, period=self.param_name)
        # sma_col = f'sma_{self.param_name}'  # Get column names

        # TODO: 2. ALWAYS shift indicators to use previous bar values (matches live trading)
        # data[sma_col] = data[sma_col].shift(1)

        # 3. Initialize signal columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # TODO: 4. Generate Entry Signals
        # condition_1_buy = data[f"sma_{self.param_name}"] > data[f"sma_{self.param_name}"]
        # condition_1_sell = data[f"sma_{self.param_name}"] < data[f"sma_{self.param_name}"]

        # TODO: 5. Generate Exit Signals
        # condition_1_close_buy = data[f"sma_{self.param_name}"] < data[f"sma_{self.param_name}"]
        # condition_1_close_sell = data[f"sma_{self.param_name}"] > data[f"sma_{self.param_name}"]

        # TODO: 6. Set Entry signals
        # data.loc[condition_1_buy, "entry_signal"] = 1
        # data.loc[condition_1_buy, 'price'] = data.loc[condition_1_buy, 'open']

        # data.loc[condition_1_sell, "entry_signal"] = -1
        # data.loc[condition_1_sell, 'price'] = data.loc[condition_1_sell, 'open']

        # TODO: 6. Set Exit signals
        # data.loc[condition_1_close_buy, "exit_signal"] = 1  # Exit Buy
        # data.loc[condition_1_close_buy, 'price'] = data.loc[condition_1_close_buy, 'open']

        # data.loc[condition_1_close_sell, "exit_signal"] = -1 # Exit Sell
        # data.loc[condition_1_close_sell, 'price'] = data.loc[condition_1_close_sell, 'open']

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        """Parse the signal at a specific index into a standardized SignalDict."""
        bar = data.iloc[index]

        entry = int(bar.get("entry_signal", 0))
        exit_sig = int(bar.get("exit_signal", 0))
        pending = int(bar.get("pending_signal", 0))
        cancel = int(bar.get("cancel_pending_signal", 0))

        if entry == 0 and exit_sig == 0 and pending == 0 and cancel == 0:
            return None

        # Get price (fallback to close if None/NaN for safety, though strategies usually set it)
        price = bar.get("price")
        if pd.isna(price):
            price = bar["close"]

        # Initialize result variables
        reason = "Signal detected"
        stop_loss = None
        take_profit = None

        # Example custom logic:
        if entry == 1:
            reason = "Template buy signal"
            # stop_loss = price * 0.99
        elif entry == -1:
            reason = "Template sell signal"

        return {
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "pending_signal": pending,
            "cancel_pending_signal": cancel,
            "price": float(price),
            "time": bar.name,
            "reason": reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
