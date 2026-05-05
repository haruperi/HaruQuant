"""10 Bollinger Trend Following Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.strategy import BaseStrategy
from haruquant.strategy import SignalDict
from haruquant.indicator import bbands

class BollingerTrendFollowingStrategy(BaseStrategy):
    """
    10 Bollinger Bands Trend Following Strategy.
    
    Trend following strategy using Bollinger Bands.
    Buys when price breaks above upper band, sells when price breaks below lower band.
    
    Entry Signals:
    - Long: Buy when close > upper Bollinger Band (follow the breakout up)
    - Short: Sell when close < lower Bollinger Band (follow the breakout down)
    
    Exit Strategy:
    - Always in the market - exits only when opposite signal occurs
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Calculate BBands(20, 2.0)
        data = bbands(data, period=20, std_dev=2.0, price_col="close")
        suffix = "20_2" # int 2.0 -> 2
        upper_col = f"bb_upper_{suffix}"
        lower_col = f"bb_lower_{suffix}"
        
        # Compare "Previous Close" vs "Previous Upper Band".
        data["prev_close"] = data["close"].shift(1)
        data["prev_upper"] = data[upper_col].shift(1)
        data["prev_lower"] = data[lower_col].shift(1)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Long: Close > Upper
        long_cond = data["prev_close"] > data["prev_upper"]
        
        # Short: Close < Lower
        short_cond = data["prev_close"] < data["prev_lower"]
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
