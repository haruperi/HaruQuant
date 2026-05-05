"""07 Close Mean Reversion Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict

class CloseMeanReversionStrategy(BaseStrategy):
    """
    07 Close Mean Reversion Strategy.
    
    Simple mean reversion strategy based on daily close prices.
    Buys when price closes down, sells when price closes up.
    
    Entry Signals:
    - Long: Buy when close < previous close (fade the down day)
    - Short: Sell when close > previous close (fade the up day)
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Shift(1) gives us logic for "Previous Bar" vs "Previous-Previous Bar".
        # We want to check "Previous Bar Close" vs "Previous Previous Bar Close".
        # If Prev Close < Prev Prev Close -> Buy (Execute on Current Open).
        
        data["curr_close"] = data["close"].shift(1)
        data["prev_close"] = data["curr_close"].shift(1)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Long: Prev Close < Prev Prev Close (Down day)
        long_cond = data["curr_close"] < data["prev_close"]
        
        # Short: Prev Close > Prev Prev Close (Up day)
        short_cond = data["curr_close"] > data["prev_close"]
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
