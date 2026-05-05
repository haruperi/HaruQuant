"""
Mean Reversion Strategy

Bollinger Bands + RSI strategy for counter-trend trading.

Entry Signals:
- LONG: Price touches lower BB AND RSI < oversold threshold
- SHORT: Price touches upper BB AND RSI > overbought threshold

Exit Signals:
- Price returns to middle BB
- Opposite entry condition triggers
"""

from typing import Optional, Dict, Any
import pandas as pd
from apps.indicator import bbands, rsi
from apps.utils.logger import logger
from apps.strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy using Bollinger Bands and RSI

    Counter-trend strategy that buys oversold conditions and sells overbought conditions.
    Uses Bollinger Bands to identify price extremes and RSI to confirm momentum exhaustion.

    This strategy:
    - Identifies overbought/oversold conditions
    - Enters when price is at extremes
    - Exits when price returns to mean
    - Uses confluence of BB and RSI for stronger signals

    Parameters (via params dict):
        bb_period: Bollinger Bands period (default: 20)
        bb_std: Bollinger Bands standard deviation (default: 2.0)
        rsi_period: RSI period (default: 14)
        rsi_oversold: RSI oversold threshold (default: 30)
        rsi_overbought: RSI overbought threshold (default: 70)
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize mean reversion strategy.

        Args:
            params: Strategy parameters dict with keys:
                - symbol: Trading symbol (e.g., "EURUSD")
                - bb_period: Bollinger Bands period (default: 20)
                - bb_std: BB standard deviation (default: 2.0)
                - rsi_period: RSI period (default: 14)
                - rsi_oversold: Oversold threshold (default: 30)
                - rsi_overbought: Overbought threshold (default: 70)
        
        Example:
            strategy = MeanReversionStrategy(   {
                'symbol': 'EURUSD',
                'bb_period': 20,
                'bb_std': 2.0,
                'rsi_period': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70
            })
        """
        super().__init__(params)

        # Extract parameters with defaults
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
        self.rsi_period = self.params.get('rsi_period', 12)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)

        # Validate parameters
        if self.bb_period <= 0:
            raise ValueError(f"bb_period must be positive, got {self.bb_period}")

        if self.bb_std <= 0:
            raise ValueError(f"bb_std must be positive, got {self.bb_std}")

        if not (0 < self.rsi_oversold < self.rsi_overbought < 100):
            raise ValueError(
                f"RSI thresholds must satisfy: 0 < oversold < overbought < 100, "
                f"got oversold={self.rsi_oversold}, overbought={self.rsi_overbought}"
            )

    def on_init(self) -> None:
        """Initialize strategy."""
        logger.info(f"MeanReversion initialized for {self.params['symbol']}")
        logger.info(
            f"Parameters: BB({self.bb_period},{self.bb_std}), "
            f"RSI({self.rsi_period}), "
            f"Oversold<{self.rsi_oversold}, Overbought>{self.rsi_overbought}"
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators and detect mean reversion conditions.

        Adds:
        - bb_upper/middle/lower: Bollinger Bands (shifted)
        - rsi: RSI (shifted)
        - signal: 'buy', 'sell'
        - price: entry price (open)
        
        Note: Indicators are shifted by 1 to use previous bar values for signal generation
        at the open of the current bar.
        """
        # Calculate indicators
        data = bbands(data, self.bb_period, self.bb_std)
        data = rsi(data, self.rsi_period)

        # Get column names
        bb_upper_col = f'bb_upper_{self.bb_period}_{int(self.bb_std)}'
        bb_middle_col = f'bb_middle_{self.bb_period}_{int(self.bb_std)}'
        bb_lower_col = f'bb_lower_{self.bb_period}_{int(self.bb_std)}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        # Shift indicators and price to use previous bar values
        # We use previous close to compare against previous bands
        data[bb_upper_col] = data[bb_upper_col].shift(1)
        data[bb_middle_col] = data[bb_middle_col].shift(1)
        data[bb_lower_col] = data[bb_lower_col].shift(1)
        data[rsi_col] = data[rsi_col].shift(1)
        data['prev_close'] = data['close'].shift(1)

        # Initialize signal columns
        data['entry_signal'] = 0
        data['exit_signal'] = 0
        data['pending_signal'] = 0
        data['cancel_pending_signal'] = 0
        data['price'] = float('nan')

        # Define Conditions (using shifted values)
        # LONG: Previous Close <= Previous Lower BB AND Previous RSI < Oversold
        condition_buy = (data['prev_close'] <= data[bb_lower_col]) & (data[rsi_col] < self.rsi_oversold)
        
        # SHORT: Previous Close >= Previous Upper BB AND Previous RSI > Overbought
        condition_sell = (data['prev_close'] >= data[bb_upper_col]) & (data[rsi_col] > self.rsi_overbought)

        # Populate signals
        # Populate signals
        data.loc[condition_buy, 'entry_signal'] = 1
        data.loc[condition_buy, 'price'] = data.loc[condition_buy, 'open']
        
        data.loc[condition_sell, 'entry_signal'] = -1
        data.loc[condition_sell, 'price'] = data.loc[condition_sell, 'open']

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[Dict[str, Any]]:
        """
        Get signal details for a specific bar.
        """
        row = data.iloc[index]
        entry = row['entry_signal']
        # Exit logic for mean reversion is implicit (TP/SL) or could be added here
        
        if entry == 0:
            return None

        # Get bar data
        bar = data.iloc[index]
        entry_price = bar['price']
        
        bb_upper = bar[f'bb_upper_{self.bb_period}_{int(self.bb_std)}']
        bb_middle = bar[f'bb_middle_{self.bb_period}_{int(self.bb_std)}']
        bb_lower = bar[f'bb_lower_{self.bb_period}_{int(self.bb_std)}']
        rsi_value = bar[f'rsi_{self.rsi_period}']

        # Variables init
        reason = None
        entry_signal = 0
        sl = None
        tp = None

        if entry == 1:
            # SL: Below lower BB by band width (volatility based)
            band_width = bb_upper - bb_lower
            sl = entry_price - (band_width * 0.5) 
            tp = bb_middle # Target Mean
            
            reason = f"Oversold: PrevClose <= BB_Lower & RSI({rsi_value:.1f}) < {self.rsi_oversold}"
            entry_signal = 1
            
        elif entry == -1:
            # SL: Above upper BB by band width
            band_width = bb_upper - bb_lower
            sl = entry_price + (band_width * 0.5)
            tp = bb_middle # Target Mean
            
            reason = f"Overbought: PrevClose >= BB_Upper & RSI({rsi_value:.1f}) > {self.rsi_overbought}"
            entry_signal = -1
        else:
            return None

        return {
            'entry_signal': entry_signal,
            'exit_signal': 0,
            'pending_signal': 0,
            'cancel_pending_signal': 0,
            'time': bar.name,
            'reason': reason,
            'price': entry_price,
            'stop_loss': sl,
            'take_profit': tp,
            'rsi': rsi_value
        }
