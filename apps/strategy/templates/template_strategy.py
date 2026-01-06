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

from apps.logger import logger
from apps.strategy import BaseStrategy

# Import indicators as needed
# from apps.indicator import atr, ema, rsi, sma


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

        Signal values:
         - 'buy': Market buy signal
         - 'sell': Market sell signal
         - 'buy stop': Pending buy stop signal
         - 'sell stop': Pending sell stop signal
         - 'buy limit': Pending buy limit signal
         - 'sell limit': Pending sell limit signal
         - 'close buy': Close buy signal
         - 'close sell': Close sell signal

        """
        # TODO: 1. Calculate your indicators here
        # data = sma(data, period=self.param_name)
        # sma_col = f'sma_{self.param_name}'  # Get column names

        # TODO: 2. ALWAYS shift indicators to use previous bar values (matches live trading)
        # data[sma_col] = data[sma_col].shift(1)

        # 3. Initialize signal columns
        data["signal"] = None
        data["price"] = float("nan")

        # TODO: 4. Generate Entry Signals
        # condition_1_buy = data[f"sma_{self.param_name}"] > data[f"sma_{self.param_name}"]
        # condition_1_sell = data[f"sma_{self.param_name}"] < data[f"sma_{self.param_name}"]

        # TODO: 5. Generate Exit Signals
        # condition_1_close_buy = data[f"sma_{self.param_name}"] < data[f"sma_{self.param_name}"]
        # condition_1_close_sell = data[f"sma_{self.param_name}"] > data[f"sma_{self.param_name}"]

        # TODO: 6. Set Entry signals
        # data.loc[condition_1_buy, "signal"] = "buy"
        # data.loc[condition_1_buy, 'price'] = data.loc[condition_1_buy, 'open']

        # data.loc[condition_1_sell, "signal"] = "sell"
        # data.loc[condition_1_sell, 'price'] = data.loc[condition_1_sell, 'open']

        # TODO: 6. Set Exit signals
        # data.loc[condition_1_close_buy, "signal"] = "close buy"
        # data.loc[condition_1_close_buy, 'price'] = data.loc[condition_1_close_buy, 'open']

        # data.loc[condition_1_close_sell, 'price'] = data.loc[condition_1_close_sell, 'open']
        # data.loc[condition_1_close_sell, "signal"] = "close sell"

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
        """
        Parse the signal at a specific index into a standardized dictionary.

        This is used by the execution engine/demo to understand the signal.
        """
        signal_type = data.iloc[index]["signal"]

        if signal_type is None:
            return None

        # Get bar data
        bar = data.iloc[index]
        entry_price = bar["price"]

        # Initialize result variables
        reason = None
        signal_name = None  # Display name like "Buy Stop", "Sell Limit"
        stop_loss = None
        take_profit = None

        if signal_type == "buy":  # Market Buy
            reason = "Template buy signal triggered"
            signal_name = "buy"
            # Optional: Calculate SL/TP
            # stop_loss = entry_price * 0.99

        elif signal_type == "sell":  # Market Sell
            reason = "Template sell signal triggered"
            signal_name = "sell"

        elif signal_type == "buy stop":  # Pending Buy Stop
            reason = f"Buy Stop at {entry_price}"
            signal_name = "buy stop"

        elif signal_type == "sell stop":  # Pending Sell Stop
            reason = f"Sell Stop at {entry_price}"
            signal_name = "sell stop"

        elif signal_type == "buy limit":  # Pending Buy Limit
            reason = f"Buy Limit at {entry_price}"
            signal_name = "buy limit"

        elif signal_type == "sell limit":  # Pending Sell Limit
            reason = f"Sell Limit at {entry_price}"
            signal_name = "sell limit"

        elif signal_type == "close buy":  # Close Buy
            reason = "Template close buy signal triggered"
            signal_name = "close buy"

        elif signal_type == "close sell":  # Close Sell
            reason = "Template close sell signal triggered"
            signal_name = "close sell"

        else:
            return None

        return {
            "signal": signal_name,
            "time": bar.name,
            "reason": reason,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
