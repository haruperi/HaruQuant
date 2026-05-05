"""03 Mean Reversion Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.trading import PositionType

class MeanReversionStrategy(BaseStrategy):
    """
    03 Mean Reversion Strategy.
    
    Tests if the instrument has an edge in mean reversion strategies.
    Sells when price reaches previous high, buys when price reaches previous low.
    
    Entry Signals:
    - Long: Buy at previous bar's low (limit order - fade the move down)
    - Short: Sell at previous bar's high (limit order - fade the move up)
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
        if index < 1:
            return None
            
        row = data.iloc[index]
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
        
        # Mean Reversion:
        # If Long, we generally want to Exit at High or Reverse at High?
        # Strategy says: "Always in the market - exits only when opposite signal occurs"
        # "Short: Sell at previous bar's high"
        # So if Long, we place Sell Limit at Prev High to reverse to Short.
        
        if is_long:
            # Place Sell Limit at Prev High
            pending_signal = -2 # Sell Limit
            price = prev_high
        elif is_short:
            # Place Buy Limit at Prev Low
            pending_signal = 2 # Buy Limit
            price = prev_low
        else:
            # Flat: Which one? 
            # Fade the move.
            # If Prev Close > Prev Open (Bullish), we expect reversion?
            # Or do we simply place BOTH?
            # Limitation: Can only place one.
            # Bias: If Bullish Candle, price is likely going UP, so we want to SHORT at High?
            # If Bearish Candle, price is likely going DOWN, so we want to BUY at Low?
            
            prev_bar = data.iloc[index-1]
            if prev_bar["close"] > prev_bar["open"]:
                # Bullish previous bar -> Expect it to hit high then reverse?
                # Sell Limit at High
                pending_signal = -2
                price = prev_high
            else:
                # Bearish previous bar -> Buy Limit at Low
                pending_signal = 2
                price = prev_low

        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": pending_signal,
            "cancel_pending_signal": 1,
            "price": float(price) if pending_signal != 0 else None,
            "time": row.name,
            "reason": "03 Mean Reversion",
            "stop_loss": None,
            "take_profit": None
        }
