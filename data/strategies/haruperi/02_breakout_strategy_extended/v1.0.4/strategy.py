"""02 Extended Breakout Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.strategy import BaseStrategy
from haruquant.strategy import SignalDict
from haruquant.strategy import PositionType

class ExtendedBreakoutStrategy(BaseStrategy):
    """
    02 Extended Breakout / Trend Following Strategy.
    
    Entry Signals:
    - Long: Buy at previous bar's high when close > open AND close > previous close
    - Short: Sell at previous bar's low when close < open AND close < previous close
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
        if index < 2: # Need prev and prev-prev
            return None
            
        row = data.iloc[index]
        prev_bar = data.iloc[index-1]
        prev_prev_bar = data.iloc[index-2] # To check 'previous close' relative to prev bar
        
        prev_high = row.get("prev_high")
        prev_low = row.get("prev_low")
        
        if pd.isna(prev_high) or pd.isna(prev_low):
            return None

        # Check Position
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
        
        # Conditions for Trend Confirmation on PREVIOUS bar
        # Long: close > open AND close > previous close
        bullish_setup = (prev_bar["close"] > prev_bar["open"]) and (prev_bar["close"] > prev_prev_bar["close"])
        
        # Short: close < open AND close < previous close
        bearish_setup = (prev_bar["close"] < prev_bar["open"]) and (prev_bar["close"] < prev_prev_bar["close"])

        if is_long:
            # We are Long. We only reverse if we get a valid Bearish Setup?
            # Or do we always place a stop to reverse?
            # "Always in the market - exits only when opposite signal occurs" matches Breakout.
            # But "Only takes breakout signals when the close is in the direction of the trend."
            # This implies filtering the entry.
            # If we are Long, and we don't have a Bearish Setup, we probably shouldn't place a Sell Stop?
            # But if we don't place a Sell Stop, we hold Long.
            # If price crashes down, we hold?
            # Breakout strategies usually rely on the stop to reverse.
            # Let's assume: If setup matches, place stop. If not, maybe do nothing (hold)?
            # Or cancel pending if no invalid setup.
            
            if bearish_setup:
                pending_signal = -1 # Sell Stop
                price = prev_low
            else:
                # No new signal, so we remain Long. 
                # We should probably cancel strictly if we want to be pure.
                # But 'cancel_pending_signal' is 1 usually.
                pass
                
        elif is_short:
            if bullish_setup:
                pending_signal = 1 # Buy Stop
                price = prev_high
        else:
            # Flat
            if bullish_setup:
                pending_signal = 1
                price = prev_high
            elif bearish_setup:
                pending_signal = -1
                price = prev_low
                
        # If pending_signal is 0, we still return it to potentially CANCEL existing orders
        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": pending_signal,
            "cancel_pending_signal": 1,
            "price": float(price) if pending_signal != 0 else None,
            "time": row.name,
            "reason": "02 Extended Breakout",
            "stop_loss": None,
            "take_profit": None
        }
