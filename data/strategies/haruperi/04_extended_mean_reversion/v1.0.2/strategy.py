"""04 Extended Mean Reversion Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.strategy import BaseStrategy
from haruquant.strategy import SignalDict
from haruquant.strategy import PositionType

class ExtendedMeanReversionStrategy(BaseStrategy):
    """
    04 Extended Mean Reversion Strategy.
    
    Enhanced mean reversion strategy that fades strong momentum moves.
    Sells into bullish candles at highs, buys into bearish candles at lows.
    
    Entry Signals:
    - Short: Sell at previous high when close > open AND close > previous close (fade bullish momentum)
    - Long: Buy at previous low when close < open AND close < previous close (fade bearish momentum)
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        data["prev_high"] = data["high"].shift(1)
        data["prev_low"] = data["low"].shift(1)
        data["pending_signal"] = 1
        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        """Generate pending signals."""
        if index < 2:
            return None
            
        row = data.iloc[index]
        prev_bar = data.iloc[index-1]
        prev_prev_bar = data.iloc[index-2]
        
        prev_high = row.get("prev_high")
        prev_low = row.get("prev_low")
        
        if pd.isna(prev_high) or pd.isna(prev_low):
            return None

        is_long = False
        is_short = False
        if self.position and hasattr(self.position, "positions"):
             for pos in self.position.positions.values():
                 if pos.symbol == self.symbol:
                     if pos.type == PositionType.BUY:
                         is_long = True
                     elif pos.type == PositionType.SELL:
                         is_short = True
                     break
        
        pending_signal = 0
        price = 0.0
        
        # Bullish Momentum Setup (to fade)
        bullish_setup = (prev_bar["close"] > prev_bar["open"]) and (prev_bar["close"] > prev_prev_bar["close"])
        
        # Bearish Momentum Setup (to fade)
        bearish_setup = (prev_bar["close"] < prev_bar["open"]) and (prev_bar["close"] < prev_prev_bar["close"])

        if is_long:
            # If Long, looking to Short (Reverse) at High if Bullish Momentum
            if bullish_setup:
                pending_signal = -2 # Sell Limit
                price = prev_high
        elif is_short:
            # If Short, looking to Buy (Reverse) at Low if Bearish Momentum
            if bearish_setup:
                pending_signal = 2 # Buy Limit
                price = prev_low
        else:
            # Flat
            if bullish_setup:
                pending_signal = -2 # Sell Limit (Fade)
                price = prev_high
            elif bearish_setup:
                pending_signal = 2 # Buy Limit (Fade)
                price = prev_low

        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": pending_signal,
            "cancel_pending_signal": 1,
            "price": float(price) if pending_signal != 0 else None,
            "time": row.name,
            "reason": "04 Ext Mean Reversion",
            "stop_loss": None,
            "take_profit": None
        }
