"""05 RSI Mean Reversion Strategy."""

from typing import Any, Dict, Optional
import pandas as pd
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.indicator import rsi

class RSIMeanReversionStrategy(BaseStrategy):
    """
    05 RSI Mean Reversion Strategy.
    
    Mean reversion strategy using RSI indicator.
    Buys when RSI is oversold, sells when RSI is overbought.
    
    Entry Signals:
    - Long: Buy when RSI(2) < 25 (oversold)
    - Short: Sell when RSI(2) > 75 (overbought)
    
    Exit Strategy:
    - Always in the market - exits only when opposite signal occurs
    """

    def on_init(self) -> None:
        """Initialize."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals."""
        # Calculate RSI(2)
        data = rsi(data, period=2, price_col="close")
        
        # Initialize columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        
        # Generate Signals
        # We use previous bar RSI to avoid look-ahead bias if 'close' is strictly current close?
        # Standard backtest assumes decisions on completed bars (shift 1).
        # apps.backtest.engine.event_driven uses "current bar" but typically strategies use shifting.
        # However, `trend_following.py` shifts explicitely.
        # "prev_fast" etc.
        # If I use `data['rsi_2']`, it includes current bar.
        # If execution is at Open of Bar N, we use Close of Bar N-1.
        # Engine Logic:
        # `is_trading_timeframe`: signal_idx = i. signal_bar = data.iloc[i].
        # Execute at `bar['open']`.
        # So `signal_bar` includes `close`. If we use `close` to generate signal, and execute at `open` of SAME bar,
        # that is lookahead bias (using future close).
        # We MUST shift signals or indicators.
        
        rsi_col = "rsi_2"
        data["prev_rsi"] = data[rsi_col].shift(1)
        
        # Long: Prev RSI < 25
        long_cond = data["prev_rsi"] < 25
        
        # Short: Prev RSI > 75
        short_cond = data["prev_rsi"] > 75
        
        data.loc[long_cond, "entry_signal"] = 1
        data.loc[short_cond, "entry_signal"] = -1
        
        # Price for logging/reference (Market Order uses Open anyway)
        data.loc[long_cond, "price"] = data.loc[long_cond, "open"]
        data.loc[short_cond, "price"] = data.loc[short_cond, "open"]
        
        return data
