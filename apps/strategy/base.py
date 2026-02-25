"""
Base Strategy.

Abstract base class for all trading strategies.
Simplified API with signal-based approach.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, TypedDict

import pandas as pd

# Avoid circular imports
if TYPE_CHECKING:
    from apps.trading import AccountInfo, OrderInfo, PositionInfo, SymbolInfo, Trade


class SignalDict(TypedDict, total=False):
    """
    Signal dictionary structure.

    Keys:
        entry_signal: 1 (Buy), -1 (Sell), 0 (None)
        exit_signal: 1 (Exit Buy), -1 (Exit Sell), 0 (None)
        pending_signal: 1 (Buy Stop), -1 (Sell Stop), 2 (Buy Limit), -2 (Sell Limit), 0 (None)
        cancel_pending_signal: 1 (Cancel Buy Stop), -1 (Cancel Sell Stop), ...
        price: Price for entry/pending
        stop_loss: Preventative stop loss
        take_profit: Profit target
        reason: Text description of the signal
        time: Timestamp of the signal
    """

    entry_signal: Optional[int]
    exit_signal: Optional[int]
    pending_signal: Optional[int]
    cancel_pending_signal: Optional[int]
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    reason: Optional[str]
    time: Any


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    Strategies are pure logic - they:
    - Calculate indicators
    - Generate signals via DataFrame columns
    - Return signal details when requested

    Simple lifecycle:
    1. on_init() - Initialize strategy
    2. on_bar() - Calculate indicators and add signal columns
    3. get_signal() - Get signal details for specific bar

    Required Columns in on_bar:
    - entry_signal: 1 (Buy), -1 (Sell)
    - exit_signal: 1 (Exit Buy), -1 (Exit Sell)
    - pending_signal: 1 (Buy Stop), -1 (Sell Stop), 2 (Buy Limit), -2 (Sell Limit)
    - cancel_pending_signal: matching pending enum
    - price: Price for entries/pendings
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy.

        Args:
            params: Strategy parameters dict (e.g., {'symbol': 'EURUSD', 'ema_fast': 20})
        """
        self.params = params or {}
        if "symbol" not in self.params:
            self.params["symbol"] = "UNKNOWN"

        # Extract symbol from params (required for backtest engines)
        self.symbol = self.params["symbol"]

        # Optional trading objects (injected by engines for live/backtest)
        self.trade: Optional["Trade"] = None
        self.account: Optional["AccountInfo"] = None
        self.position: Optional["PositionInfo"] = None
        self.order: Optional["OrderInfo"] = None
        self.symbol_info: Optional["SymbolInfo"] = None

    # =====================================================================
    # LIFECYCLE METHODS
    # =====================================================================

    @abstractmethod
    def on_init(self) -> None:
        """
        Initialize strategy (optional).

        Called once before processing data.
        Use this to:
        - Validate parameters
        - Set up internal state
        - Log initialization

        """
        pass

    def on_tick(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process tick data (optional).

        For live trading tick-by-tick processing.
        Most strategies can ignore this.

        Args:
            data: Tick data DataFrame

        Returns:
            Updated DataFrame

        Note:
            Not all engines support tick processing.
        """
        return data

    @abstractmethod
    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators and add signal columns.

        This is the main strategy logic. Called with entire DataFrame.
        Should:
        1. Calculate all indicators (EMA, ATR, RSI, etc.)
        2. Add signal columns:
           - entry_signal: 1 (Buy), -1 (Sell)
           - exit_signal: 1 (Exit Buy), -1 (Exit Sell)
           - pending_signal: ...
           - price: ...

        Args:
            data: OHLCV DataFrame

        Returns:
            DataFrame with indicators and signal columns added
        """
        pass

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        """
        Get signal details for a specific bar.

        Args:
            data: DataFrame with indicators and signal columns
            index: Index of the bar to get signal for

        Returns:
            SignalDict with keys:
                - entry_signal, exit_signal, pending_signal...
                - time: Timestamp of the signal
                - reason: Human-readable reason for signal
                - stop_loss: Stop loss price (optional)
                - take_profit: Take profit price (optional)
            or None if no signal at that index
        """
        row = data.iloc[index]

        # Check if any signal exists
        entry = row.get("entry_signal", 0) or 0
        exit_sig = row.get("exit_signal", 0) or 0
        pending = row.get("pending_signal", 0) or 0
        cancel = row.get("cancel_pending_signal", 0) or 0

        if entry == 0 and exit_sig == 0 and pending == 0 and cancel == 0:
            return None

        # Build basic signal dict - strategy implementations can override to add specific reasons/SL/TP
        return {
            "entry_signal": int(entry),
            "exit_signal": int(exit_sig),
            "pending_signal": int(pending),
            "cancel_pending_signal": int(cancel),
            "price": (
                float(row.get("price", 0.0)) if pd.notna(row.get("price")) else None
            ),
            "time": data.index[index],
            "reason": "Signal detected",
            "stop_loss": None,
            "take_profit": None,
        }

    # =====================================================================
    # HELPER METHODS
    # =====================================================================

    def get_indicator_value(
        self, data: pd.DataFrame, column: str, offset: int = 0
    ) -> Optional[float]:
        """
        Get indicator value from data.

        Args:
            data: DataFrame with indicators
            column: Indicator column name (e.g., 'ema_20', 'rsi_14')
            offset: Bars back (0 = current, 1 = previous, etc.)

        Returns:
            Indicator value or None if not available or NaN

        Example:
            current_ema = self.get_indicator_value(data, 'ema_20', offset=0)
            previous_rsi = self.get_indicator_value(data, 'rsi_14', offset=1)
        """
        if data is None or len(data) <= offset:
            return None

        try:
            value = data.iloc[-(offset + 1)][column]
            return None if pd.isna(value) else value
        except (KeyError, IndexError):
            return None

    def crossover(self, series1: pd.Series, series2: pd.Series) -> bool:
        """
        Detect bullish crossover where series1 crosses above series2.

        Checks if series1 was below/equal to series2 on previous bar
        and is now above series2 on current bar.

        Args:
            series1: Fast series (e.g., EMA 20)
            series2: Slow series (e.g., EMA 50)

        Returns:
            True if crossover occurred on latest bar, False otherwise

        Example:
            if self.crossover(data['ema_20'], data['ema_50']):
                # EMA(20) just crossed above EMA(50) - bullish signal
                pass
        """
        if len(series1) < 2 or len(series2) < 2:
            return False

        # Previous bar: series1 was below or equal
        prev_below = series1.iloc[-2] <= series2.iloc[-2]

        # Current bar: series1 is above
        curr_above = series1.iloc[-1] > series2.iloc[-1]

        return bool(prev_below and curr_above)

    def crossunder(self, series1: pd.Series, series2: pd.Series) -> bool:
        """
        Detect bearish crossunder where series1 crosses below series2.

        Checks if series1 was above/equal to series2 on previous bar
        and is now below series2 on current bar.

        Args:
            series1: Fast series (e.g., EMA 20)
            series2: Slow series (e.g., EMA 50)

        Returns:
            True if crossunder occurred on latest bar, False otherwise

        Example:
            if self.crossunder(data['ema_20'], data['ema_50']):
                # EMA(20) just crossed below EMA(50) - bearish signal
                pass
        """
        if len(series1) < 2 or len(series2) < 2:
            return False

        # Previous bar: series1 was above or equal
        prev_above = series1.iloc[-2] >= series2.iloc[-2]

        # Current bar: series1 is below
        curr_below = series1.iloc[-1] < series2.iloc[-1]

        return bool(prev_above and curr_below)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return f"{self.__class__.__name__}({self.params})"
