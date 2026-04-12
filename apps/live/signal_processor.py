"""Signal Processor.

Maintains rolling window of bars and runs strategy to detect trading signals.
Handles strategy initialization and real-time signal detection.
"""

from typing import Optional

import pandas as pd

from backend.common.logger import logger
from apps.strategy.base import BaseStrategy, SignalDict


class SignalProcessor:
    """Process bars through strategy and detect signals."""

    def __init__(self, strategy: BaseStrategy, max_bars: int = 500):
        """Initialize signal processor.

        Args:
            strategy: Strategy instance (e.g., TrendFollowingStrategy)
            max_bars: Maximum bars to keep in rolling window
        """
        self.strategy = strategy
        self.max_bars = max_bars
        self._data: Optional[pd.DataFrame] = None
        self._initialized = False

        logger.info(f"SignalProcessor initialized with {strategy.__class__.__name__}")

    def initialize(self, historical_data: pd.DataFrame) -> bool:
        """Initialize with historical data.

        Args:
            historical_data: DataFrame with at least 200+ bars for EMA calculation

        Returns:
            True if initialization successful
        """
        try:
            if historical_data is None or historical_data.empty:
                logger.error("Cannot initialize with empty historical data")
                return False

            logger.info(f"Initializing strategy with {len(historical_data)} bars")

            # Run strategy on historical data
            self._data = self.strategy.on_bar(historical_data.copy())

            # Verify indicators were calculated
            if self._data is None or self._data.empty:
                logger.error("Strategy returned empty data")
                return False

            logger.info(
                f"Strategy initialized successfully. Data shape: {self._data.shape}"
            )
            logger.debug(f"Available columns: {list(self._data.columns)}")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Error initializing signal processor: {e}", exc_info=True)
            return False

    def update_with_new_bar(self, new_bar: pd.Series) -> Optional[SignalDict]:
        """Update rolling window with new bar and check for signals.

        Args:
            new_bar: New bar data (Series with OHLCV)

        Returns:
            Signal dictionary if signal detected, None otherwise
        """
        if not self._initialized:
            logger.error("Signal processor not initialized. Call initialize() first.")
            return None

        try:
            self._append_new_bar(new_bar)
            self._data = self.strategy.on_bar(self._data)

            last_index = len(self._data) - 1
            signal = self.strategy.get_signal(self._data, last_index)
            if signal:
                self._log_signal_details(signal)

            return signal

        except Exception as e:
            logger.error(f"Error processing new bar: {e}", exc_info=True)
            return None

    def _append_new_bar(self, new_bar: pd.Series) -> None:
        if isinstance(new_bar, pd.Series):
            new_bar_df = pd.DataFrame([new_bar])
        else:
            new_bar_df = new_bar

        self._data = pd.concat([self._data, new_bar_df], ignore_index=False)

        if len(self._data) > self.max_bars:
            self._data = self._data.iloc[-self.max_bars :]
            logger.debug(f"Trimmed data to {self.max_bars} bars")

    def _extract_signal_label(self, signal: SignalDict) -> str:
        signal_label = signal.get("signal")
        if signal_label:
            return str(signal_label)

        entry_signal = signal.get("entry_signal")
        exit_signal = signal.get("exit_signal")
        if entry_signal in (1, -1):
            return "entry_buy" if entry_signal == 1 else "entry_sell"
        if exit_signal in (1, -1):
            return "exit_buy" if exit_signal == 1 else "exit_sell"
        return "signal"

    def _log_signal_details(self, signal: SignalDict) -> None:
        signal_label = self._extract_signal_label(signal)
        signal_time = signal.get("time", "unknown")
        logger.info(f"Signal detected: {signal_label} at {signal_time}")

        reason = signal.get("reason")
        if reason:
            logger.info(f"  Reason: {reason}")

        price = signal.get("price", signal.get("entry_price"))
        if isinstance(price, (int, float)):
            logger.info(f"  Price: {price:.5f}")

    def get_current_data(self) -> Optional[pd.DataFrame]:
        """Get current rolling window of data.

        Returns:
            DataFrame with current data window
        """
        return self._data.copy() if self._data is not None else None

    def get_last_signal(self) -> Optional[SignalDict]:
        """Get signal from the last bar in current data.

        Returns:
            Signal dictionary or None
        """
        if not self._initialized or self._data is None or self._data.empty:
            return None

        try:
            last_index = len(self._data) - 1
            return self.strategy.get_signal(self._data, last_index)
        except Exception as e:
            logger.error(f"Error getting last signal: {e}", exc_info=True)
            return None

    def is_initialized(self) -> bool:
        """Check if processor is initialized.

        Returns:
            True if initialized
        """
        return self._initialized

    def __repr__(self) -> str:
        """Return string representation of the signal processor."""
        bars_count = len(self._data) if self._data is not None else 0
        return f"SignalProcessor(strategy={self.strategy.__class__.__name__}, bars={bars_count}, initialized={self._initialized})"

