"""
Breakout Strategy.

Implements a simple breakout strategy using pending orders.
Entry Signals:
- Long: Buy at previous bar's high (stop order)
- Short: Sell at previous bar's low (stop order)

Exit Strategy:
- Always in the market - exits only when opposite signal occurs (Stop and Reverse)
- Pending signals expire after 1 bar
"""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.utils import logger
from haruquant.strategy import BaseStrategy, SignalDict

class PositionType:
    BUY = 0
    SELL = 1

class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy with Pending Orders.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def on_init(self) -> None:
        logger.info(f"BreakoutStrategy initialized for {self.params.get('symbol', 'Unknown')}")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate previous bar high/low for breakout levels.
        """
        # Calculate shifted values for previous bar reference
        data["prev_high"] = data["high"].shift(1)
        data["prev_low"] = data["low"].shift(1)
        data["prev_close"] = data["close"].shift(1)
        data["prev_open"] = data["open"].shift(1)
        
        # Initialize signal columns with 1 to ensure engine calls get_signal
        # The actual signal logic is in get_signal
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        
        # Flag all bars as potentially having signals so get_signal is called
        # We start from index 1 because index 0 has NaN prev_high
        data["pending_signal"] = 1
        data["cancel_pending_signal"] = 1
        
        # Reset first row to 0 as we can't calculate signal there
        data.iloc[0, data.columns.get_loc("pending_signal")] = 0
        data.iloc[0, data.columns.get_loc("cancel_pending_signal")] = 0

        data["price"] = float("nan")
        
        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        """
        Generate pending order signals based on breakout logic.
        """
        # Ensure enough data
        if index < 1:
            return None
            
        row = data.iloc[index]
        prev_high = row.get("prev_high")
        prev_low = row.get("prev_low")
        
        if pd.isna(prev_high) or pd.isna(prev_low):
            return None

        # Logic:
        # 1. Always cancel previous pending orders (Expire after 1 bar)
        # 2. Determine direction:
        #    - If Long: Place Sell Stop @ Prev Low (Reverse)
        #    - If Short: Place Buy Stop @ Prev High (Reverse)
        #    - If Flat: Bias based on momentum (Prev Close > Prev Open -> Buy Stop, else Sell Stop)
        
        pending_signal = 0
        price = 0.0
        
        # Determine current position direction
        # Note: self.position is available in EventDrivenEngine, but likely None in Vectorized
        is_long = False
        is_short = False
        
        if self.position and hasattr(self.position, "positions"):
             # Check if we have any open position for this symbol
             # Simplified: assuming one position per symbol for this strategy
             for pos in self.position.positions.values():
                 if pos.symbol == self.symbol:
                     if pos.type == PositionType.BUY:
                         is_long = True
                     elif pos.type == PositionType.SELL:
                         is_short = True
                     break
        
        if is_long:
            # We are Long, place Sell Stop to reverse
            pending_signal = -1 # Sell Stop
            price = prev_low
        elif is_short:
            # We are Short, place Buy Stop to reverse
            pending_signal = 1 # Buy Stop
            price = prev_high
        else:
            # Flat (or Vectorized mode without state)
            # Use Momentum Bias: If green bar, look for upside breakout. Red bar, downside.
            if row["prev_close"] > row["prev_open"]:
                pending_signal = 1 # Buy Stop
                price = prev_high
            else:
                pending_signal = -1 # Sell Stop
                price = prev_low
                
        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": int(pending_signal),
            "cancel_pending_signal": 1, # Always cancel previous
            "price": float(price),
            "time": row.name,
            "reason": "Breakout Pending",
            "stop_loss": None,
            "take_profit": None
        }
