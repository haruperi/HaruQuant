"""06 RSI Breakout Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.indicator import rsi

class RSIBreakoutStrategy(BaseStrategy):
    """
    06 RSI Breakout Strategy.
    
    Breakout/momentum strategy using RSI indicator.
    Buys when RSI is overbought (strength), sells when RSI is oversold (weakness).
    
    Entry Signals:
    - Long: Buy when RSI(2) > 75 (follow the strength)
    - Short: Sell when RSI(2) < 25 (follow the weakness)
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Calculate RSI(2)
        data = rsi(data, period=2, price_col="close")
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        rsi_col = "rsi_2"
        data["prev_rsi"] = data[rsi_col].shift(1)
        
        # Long: Prev RSI > 75
        long_cond = data["prev_rsi"] > 75
        
        # Short: Prev RSI < 25
        short_cond = data["prev_rsi"] < 25
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
