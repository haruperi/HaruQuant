"""08 Close Breakout Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict

class CloseBreakoutStrategy(BaseStrategy):
    """
    08 Close Breakout Strategy.
    
    Breakout strategy based on daily close prices.
    Buys when price closes higher than previous close, sells when lower.
    
    Entry Signals:
    - Long: Buy when close > previous close (follow the up day)
    - Short: Sell when close < previous close (follow the down day)
    - Execution: At Close of the same bar (Market Order)
    
    Exit Strategy:
    - Always in the market - exits only when opposite signal occurs
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Check Current Close vs Previous Close
        # "Buy THIS bar at close" implies using the current close to trigger.
        data["curr_close"] = data["close"].shift(1)
        data["prev_close"] = data["curr_close"].shift(1)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Long: Close > Prev Close
        long_cond = data["curr_close"] > data["prev_close"]
        
        # Short: Close < Prev Close
        short_cond = data["curr_close"] < data["prev_close"]
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        # Price: We want to execute at Open. 
        # EventDrivenEngine defaults to Open if price is not set, 
        # but to be explicit we can set it.
        # However, if we set it, we ensure clarity.
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
