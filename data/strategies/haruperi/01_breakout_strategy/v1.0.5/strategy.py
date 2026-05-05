"""01 Breakout Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.strategy import BaseStrategy
from haruquant.strategy import SignalDict
from haruquant.strategy import PositionType

class BreakoutStrategy(BaseStrategy):
    """
    01 Breakout Strategy.
    
    Tests if the instrument has an edge in breakout strategies.
    Buys when price breaks above previous day's high, shorts when price breaks below previous day's low.
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        data["prev_high"] = data["high"].shift(1)
        data["prev_low"] = data["low"].shift(1)
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # We need to process signals in get_signal, so mark all as potentially interesting
        # or we can set pending_signal here if simple enough.
        # But for pending orders logic (checking positions), it's often safer in get_signal 
        # OR we can do it here if we assume statelessness.
        # Given the requirements: "Always in the market - exits only when opposite signal occurs"
        # and "Stop and Reverse", this is best handled via pending orders that auto-close opposite.
        
        # Ideally, we set a flag to trigger get_signal for every bar
        data["pending_signal"] = 1  # Dummy value to ensure engine calls get_signal
        
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

        # Logic from user:
        # Long: Buy at previous bar's high (stop order)
        # Short: Sell at previous bar's low (stop order)
        
        # We need to know current position to know which way to flip?
        # User said: "Always in the market - exits only when opposite signal occurs"
        # "This creates a pure test of directional edge without stops or targets"
        
        # If we are long, we want a Sell Stop at Prev Low to reverse.
        # If we are short, we want a Buy Stop at Prev High to reverse.
        # If flat, we might want Both? Or one based on bias?
        # The user Breakout example used bias if flat. I will stick to that.
        
        # However, the user description says:
        # "Buys when price breaks above previous day's high, shorts when price breaks below previous day's low."
        # This implies placing *both* orders if flat? Or just one?
        # Typically "Breakout" strategy places bracket orders if flat.
        # But our engine limitation currently handles one pending signal return per call?
        # Let's check SignalDict. partial support for list? No, single int.
        # So we must prioritize.
        
        # If we follow the file provided earlier (data/strategies/breakout.py), it checks position.
        
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
        
        if is_long:
            # Place Sell Stop to reverse
            pending_signal = -1
            price = prev_low
        elif is_short:
            # Place Buy Stop to reverse
            pending_signal = 1
            price = prev_high
        else:
            # Flat: Use momentum bias like the reference implementation
            prev_close = row.get("close", 0) # actually this is 'close' of previous bar if we look at shifted?
            # on_bar data is current bar. But we shifted in on_bar? 
            # Wait, data['prev_high'] is shifted. data['close'] is current.
            # We want PREVIOUS bar close/open.
            
            # Let's re-read on_bar.
            # data["prev_high"] = data["high"].shift(1)
            # We didn't shift open/close in on_bar above. Let's get them from iloc[index-1]
            
            prev_bar = data.iloc[index-1]
            if prev_bar["close"] > prev_bar["open"]:
                # Bullish candle -> Buy Stop
                pending_signal = 1
                price = prev_high
            else:
                # Bearish candle -> Sell Stop
                pending_signal = -1
                price = prev_low
                
        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": pending_signal,
            "cancel_pending_signal": 1, # Cancel previous
            "price": float(price),
            "time": row.name,
            "reason": "01 Breakout",
            "stop_loss": None,
            "take_profit": None
        }
