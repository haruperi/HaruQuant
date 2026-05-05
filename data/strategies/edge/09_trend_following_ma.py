"""09 Trend Following MA Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.indicator import sma

class TrendFollowingMAStrategy(BaseStrategy):
    """
    09 Trend Following Moving Average Strategy.
    
    Trend following strategy based on moving average direction.
    Buys when MA is rising, sells when MA is falling.
    
    Entry Signals:
    - Long: Buy when MA(80) > MA(80) previous (uptrend)
    - Short: Sell when MA(80) < MA(80) previous (downtrend)
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Calculate SMA(80)
        data = sma(data, window=80, price_col="close")
        sma_col = "sma_80"
        
        # We need "MA(80) previous" which really means MA(80) of previous bar vs MA(80) of bar before that? 
        # Or MA(80) of Current Bar vs Prev Bar?
        # If we execute on Open, we check "Closed Bar SMA" vs "Previous Closed Bar SMA".
        # So SMA(shift 1) vs SMA(shift 2).
        
        data["prev_sma"] = data[sma_col].shift(1)
        data["prev_prev_sma"] = data[sma_col].shift(2)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Long: Prev SMA > Prev Prev SMA
        long_cond = data["prev_sma"] > data["prev_prev_sma"]
        
        # Short: Prev SMA < Prev Prev SMA
        short_cond = data["prev_sma"] < data["prev_prev_sma"]
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
