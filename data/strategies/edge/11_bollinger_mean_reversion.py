"""11 Bollinger Mean Reversion Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.indicator import bbands

class BollingerMeanReversionStrategy(BaseStrategy):
    """
    11 Bollinger Bands Mean Reversion Strategy.
    
    Mean reversion strategy using Bollinger Bands.
    Sells when price reaches upper band, buys when price reaches lower band.
    
    Entry Signals:
    - Long: Buy when close < lower Bollinger Band (fade the selloff)
    - Short: Sell when close > upper Bollinger Band (fade the rally)
    
    Exit Strategy:
    - Always in the market - exits only when opposite signal occurs
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        data = bbands(data, period=20, std_dev=2.0, price_col="close")
        suffix = "20_2"
        upper_col = f"bb_upper_{suffix}"
        lower_col = f"bb_lower_{suffix}"
        
        data["prev_close"] = data["close"].shift(1)
        data["prev_upper"] = data[upper_col].shift(1)
        data["prev_lower"] = data[lower_col].shift(1)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Long: Close < Lower
        long_cond = data["prev_close"] < data["prev_lower"]
        
        # Short: Close > Upper
        short_cond = data["prev_close"] > data["prev_upper"]
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
