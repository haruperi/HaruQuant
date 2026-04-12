"""Bar Monitor.

Detects when new bars open and fetches the last closed bar for signal processing.
Critical: Always returns CLOSED bars (index -2), never current forming bar (index -1).
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from backend.common.logger import logger
from apps.mt5.client import MT5Client


class BarMonitor:
    """Monitor bar formation and detect new bar openings."""

    def __init__(self, client: MT5Client, symbol: str, timeframe: str):
        """Initialize bar monitor.

        Args:
            client: MT5Client instance
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe string (e.g., "M1", "H1")
        """
        self.client = client
        self.symbol = symbol
        self.timeframe = timeframe
        self._last_bar_time: Optional[datetime] = None

        logger.info(f"BarMonitor initialized for {symbol} {timeframe}")

    def get_historical_data(self, count: int) -> Optional[pd.DataFrame]:
        """Fetch historical bars for strategy initialization.

        Args:
            count: Number of bars to fetch (e.g., 250)

        Returns:
            DataFrame with OHLCV data, or None if failed
        """
        try:
            logger.info(
                f"Fetching {count} historical bars for {self.symbol} {self.timeframe}"
            )

            bars = self.client.get_bars(
                symbol=self.symbol, timeframe=self.timeframe, count=count
            )

            if bars is None or bars.empty:
                logger.error(f"Failed to fetch historical data for {self.symbol}")
                return None

            logger.info(
                f"Fetched {len(bars)} bars, date range: {bars.index[0]} to {bars.index[-1]}"
            )

            # Initialize last_bar_time with the most recent bar
            if len(bars) >= 2:
                # Use second-to-last bar (last closed bar)
                self._last_bar_time = bars.index[-2]

            return bars

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}", exc_info=True)
            return None

    def check_new_bar(self) -> bool:
        """Check if a new bar has opened since last check.

        Returns:
            True if new bar detected, False otherwise
        """
        try:
            # Fetch last 2 bars
            bars = self.client.get_bars(
                symbol=self.symbol, timeframe=self.timeframe, count=2
            )

            if bars is None or len(bars) < 2:
                logger.warning("Could not fetch bars for new bar check")
                return False

            # Get the last closed bar time (second-to-last bar)
            current_bar_time = bars.index[-2]

            # First run - initialize
            if self._last_bar_time is None:
                self._last_bar_time = current_bar_time
                logger.debug(f"Initialized last_bar_time: {current_bar_time}")
                return False

            # Check if bar time changed
            if current_bar_time != self._last_bar_time:
                new_bar_time = bars.index[-1]
                logger.info(
                    f"New bar detected: {new_bar_time} (previous: {current_bar_time})"
                )
                self._last_bar_time = current_bar_time
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking for new bar: {e}", exc_info=True)
            return False

    def get_last_closed_bar(self) -> Optional[pd.Series]:
        """Get the last CLOSED bar (not current forming bar).

        CRITICAL: Returns index -2 (second-to-last), NOT index -1 (current forming bar)

        Returns:
            Series with OHLCV data for last closed bar, or None if failed
        """
        try:
            # Fetch last 2 bars
            bars = self.client.get_bars(
                symbol=self.symbol, timeframe=self.timeframe, count=2
            )

            if bars is None or len(bars) < 2:
                logger.error("Could not fetch bars for last closed bar")
                return None

            # Return second-to-last bar (the last CLOSED bar)
            last_closed = bars.iloc[-2]

            logger.debug(
                f"Last closed bar: {last_closed.name} | "
                f"O:{last_closed['open']:.5f} H:{last_closed['high']:.5f} "
                f"L:{last_closed['low']:.5f} C:{last_closed['close']:.5f}"
            )

            return last_closed

        except Exception as e:
            logger.error(f"Error getting last closed bar: {e}", exc_info=True)
            return None

    def get_current_bar_time(self) -> Optional[datetime]:
        """Get timestamp of the last closed bar.

        Returns:
            Timestamp of last closed bar, or None if unavailable
        """
        return self._last_bar_time

    def __repr__(self) -> str:
        """Return string representation of BarMonitor."""
        return f"BarMonitor(symbol={self.symbol}, timeframe={self.timeframe}, last_bar={self._last_bar_time})"

