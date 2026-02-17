"""
MT5 Trading System - Client Module.

This module provides the main client class for connecting to and interacting with
the MetaTrader 5 terminal. It handles connection management, authentication,
auto-reconnection, multi-account support, and event handling.
"""

import threading
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import MetaTrader5 as _mt5_module
import pandas as pd

from apps.utils.logger import logger

__all__ = ["MT5Api", "get_mt5_api", "MT5Client", "ConnectionState"]


class MT5Api:
    """Thin wrapper around MetaTrader5 with connection tracking."""

    def __init__(self, mt5_module: Optional[Any] = None) -> None:
        """Initialize MT5Api."""
        self._mt5 = mt5_module or _mt5_module
        self._initialized = False

    def initialize(self, *args: Any, **kwargs: Any) -> bool:
        """Initialize MT5 terminal connection."""
        ok = bool(self._mt5.initialize(*args, **kwargs))
        self._initialized = ok
        return ok

    def shutdown(self) -> bool:
        """Shutdown MT5 terminal connection."""
        ok = bool(self._mt5.shutdown())
        self._initialized = False
        return ok

    def last_error(self) -> Any:
        """Return last MT5 error."""
        return self._mt5.last_error()

    def is_initialized(self) -> bool:
        """Return whether initialize() succeeded in this process."""
        return self._initialized

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying MT5 module."""
        return getattr(self._mt5, name)


_MT5_API = MT5Api()


def get_mt5_api() -> MT5Api:
    """Return the shared MT5 API instance."""
    return _MT5_API


mt5 = get_mt5_api()


class ConnectionState(Enum):
    """
    Enumeration representing the connection state to MT5 terminal.

    Attributes:
        DISCONNECTED: Not connected to MT5 terminal
        CONNECTED: Successfully connected to MT5 terminal
        FAILED: Connection attempt failed
        INITIALIZING: Connection is being initialized
        RECONNECTING: Attempting to reconnect to MT5 terminal
    """

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    FAILED = "failed"
    INITIALIZING = "initializing"
    RECONNECTING = "reconnecting"

    def __str__(self) -> str:
        """Return string representation of the connection state."""
        return self.value

    def __repr__(self) -> str:
        """Return detailed representation of the connection state."""
        return f"ConnectionState.{self.name}"


class MT5Client:
    """
    Main client class for MetaTrader 5 terminal interaction.

    This class provides comprehensive connection management, authentication,
    auto-reconnection capabilities, multi-account support, and event handling
    for the MT5 trading system.

    Attributes:
        connection_state (ConnectionState): Current connection state
        login (int): Account login number
        password (str): Account password
        server (str): MT5 server name
        path (str): Path to MT5 terminal executable
        timeout (int): Connection timeout in seconds
        auto_reconnect_enabled (bool): Whether auto-reconnection is enabled
        retry_attempts (int): Number of retry attempts for reconnection
        retry_delay (int): Delay between retry attempts in seconds

    Example:
        >>> client = MT5Client(login=12345, password="pass", server="Server-Demo")
        >>> client.connect()
        >>> if client.is_connected():
        ...     print("Connected successfully")
        >>> client.shutdown()
    """

    def __init__(
        self,
        timeout: int = 60000,
        portable: bool = False,
    ):
        """
        Initialize the MT5Client instance.

        Args:
            timeout: Connection timeout in milliseconds (default: 60000)
            portable: Whether to use portable mode (default: False)

        Example:
            >>> client = MT5Client(timeout=30000)
            >>> client.connect(
            ...     path="C:/Program Files/MT5/terminal64.exe",
            ...     login=12345,
            ...     password="pass",
            ...     server="Server-Demo"
            ... )
        """
        logger.info("Initializing MT5Client")

        # Connection attributes
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.timeout: int = timeout
        self.portable: bool = portable

        # Configuration attributes
        self.config: Dict[str, Any] = {}
        self.config_path: str = ""

        # Multi-account support
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.current_account: str = ""

        # Event system
        self._event_handlers: Dict[str, List[Callable]] = {
            "connect": [],
            "disconnect": [],
            "error": [],
            "reconnect": [],
            "account_switch": [],
        }

        # Connection statistics
        self._connection_attempts: int = 0
        self._successful_connections: int = 0
        self._failed_connections: int = 0
        self._last_connection_time: Optional[datetime] = None
        self._total_connection_time: float = 0

        # Error tracking
        self._last_error: Optional[Tuple[int, str]] = None
        self._error_count: int = 0

        # Streaming state
        self._active_streams: Dict[str, bool] = {}
        self._stream_threads: Dict[str, threading.Thread] = {}

        # Initial Symbols
        self.initial_symbols: List[str] = [
            "AUDCAD",
            "AUDCHF",
            "AUDJPY",
            "AUDNZD",
            "AUDUSD",
            "CADCHF",
            "CADJPY",
            "CHFJPY",
            "EURAUD",
            "EURCAD",
            "EURCHF",
            "EURGBP",
            "EURJPY",
            "EURNZD",
            "EURUSD",
            "GBPAUD",
            "GBPCAD",
            "GBPCHF",
            "GBPJPY",
            "GBPNZD",
            "GBPUSD",
            "NZDCAD",
            "NZDCHF",
            "NZDJPY",
            "NZDUSD",
            "USDCHF",
            "USDCAD",
            "USDJPY",
            "XAUUSD",
            "XAUEUR",
            "XAUGBP",
            "XAUJPY",
            "XAUAUD",
            "XAUCHF",
            "XAGUSD",
            "US500",
            "US30",
            "UK100",
            "GER40",
            "NAS100",
            "USDX",
            "EURX",
        ]

        logger.info("MT5Client created (Terminal not yet connected)")

        # =============================================================================
        # CONNECTION MANAGEMENT
        # =============================================================================

    def connect(
        self,
        path: str,
        login: int,
        password: str,
        server: str,
    ) -> bool:
        """
        Connect to MT5 terminal and login to trading account.

        Args:
            path: Path to MT5 terminal executable
            login: Account login number
            password: Account password
            server: MT5 server name

        Returns:
            True if initialization and login successful, False otherwise
        """
        logger.info("Connecting to MT5 terminal")
        self.connection_state = ConnectionState.INITIALIZING
        self._connection_attempts += 1

        try:
            # 1. Start MT5 terminal
            logger.debug(f"Starting MT5 terminal from {path}")
            if not mt5.initialize(
                path=path, timeout=self.timeout, portable=self.portable
            ):
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"MT5 terminal initialization failed: {error_code} - {error_desc}"
                )
                self.connection_state = ConnectionState.FAILED
                self._failed_connections += 1
                return False

            # 2. Login to trading account
            logger.debug(f"Logging in to account {login} on server {server}")
            if not mt5.login(
                login=login,
                password=password,
                server=server,
                timeout=self.timeout,
            ):
                error_code, error_desc = mt5.last_error()
                logger.error(f"MT5 account login failed: {error_code} - {error_desc}")
                self.connection_state = ConnectionState.FAILED
                self._failed_connections += 1
                # Note: We don't shut down the terminal here, as it might stay running
                return False

            self.connection_state = ConnectionState.CONNECTED
            self._successful_connections += 1
            self._last_connection_time = datetime.now()
            self._add_to_watchlist()
            logger.info(f"Successfully logged in: account={login}, server={server}")
            return True

        except Exception as e:
            logger.error(f"MT5Client.connect: {e}")
            self.connection_state = ConnectionState.FAILED
            self._failed_connections += 1
            return False

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying MT5 API."""
        return getattr(mt5, name)

    def _add_to_watchlist(self) -> None:
        """Add all default symbols to the Market Watch."""
        try:
            symbols = self.initial_symbols
            if not symbols:
                logger.warning(
                    "No symbols found in initial_symbols to add to watchlist"
                )
                return

            # Add symbols to market watch
            count = 0
            for symbol in symbols:
                if mt5.symbol_select(symbol, True):
                    count += 1
                else:
                    logger.warning(f"Failed to add symbol {symbol} to watchlist")

            logger.success(f"Added {count} symbols to watchlist")

        except Exception as e:
            logger.error(f"Error adding symbols to watchlist: {e}")

    def is_connected(self) -> bool:
        """
        Check if client is currently connected to MT5 terminal.

        Returns:
            bool: True if connected, False otherwise

        Example:
            >>> if client.is_connected():
            ...     print("Currently connected")
        """
        logger.info("Checking connection state")
        # Check both our state and MT5's terminal info
        terminal_info = mt5.terminal_info()
        is_mt5_connected = terminal_info is not None and terminal_info.connected

        is_our_state_connected = self.connection_state == ConnectionState.CONNECTED

        connection_state = is_mt5_connected and is_our_state_connected
        logger.info(f"MT5 Connected: {connection_state}")

        return connection_state

    def shutdown(self) -> None:
        """
        Shutdown the MT5 terminal connection and clean up resources.

        This method should be called when you're done using the client to
        properly close the connection and release resources.

        Example:
            >>> client = MT5Client()
            >>> client.connect()
            >>> # ... do work ...
            >>> client.shutdown()
        """
        logger.info("Shutting down MT5 client")

        try:
            # Shutdown MT5 terminal
            mt5.shutdown()

            self.connection_state = ConnectionState.DISCONNECTED
            logger.success("MT5 client shutdown successfully")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    # =============================================================================
    # INFO DATA METHODS
    # =============================================================================

    def _get_mt5_timeframe(self, timeframe_str: str) -> int:
        """
        Convert string timeframe to MT5 constant.

        Args:
            timeframe_str: Timeframe string (e.g., "M1", "H1", "D1")

        Returns:
            MT5 timeframe constant
        """
        mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M2": mt5.TIMEFRAME_M2,
            "M3": mt5.TIMEFRAME_M3,
            "M4": mt5.TIMEFRAME_M4,
            "M5": mt5.TIMEFRAME_M5,
            "M6": mt5.TIMEFRAME_M6,
            "M10": mt5.TIMEFRAME_M10,
            "M12": mt5.TIMEFRAME_M12,
            "M15": mt5.TIMEFRAME_M15,
            "M20": mt5.TIMEFRAME_M20,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H2": mt5.TIMEFRAME_H2,
            "H3": mt5.TIMEFRAME_H3,
            "H4": mt5.TIMEFRAME_H4,
            "H6": mt5.TIMEFRAME_H6,
            "H8": mt5.TIMEFRAME_H8,
            "H12": mt5.TIMEFRAME_H12,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }

        tf = mapping.get(timeframe_str.upper())
        if tf is None:
            logger.warning(f"Unknown timeframe '{timeframe_str}', defaulting to D1")
            return int(mt5.TIMEFRAME_D1)
        return int(tf)

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        start_pos: int = 0,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get OHLCVS bars from MT5.

        Args:
            symbol: Symbol name
            timeframe: Timeframe string (e.g., "M1", "H1", "D1")
            count: Number of bars to return (used if date_from is None)
            start_pos: Start position (index) for fetching bars (used if date_from is None)
            date_from: Start date for fetching bars
            date_to: End date for fetching bars (defaults to now if date_from is set)

        Returns:
            pd.DataFrame with columns:
            ["Timestamp", "Open", "High", "Low", "Close", "Volume", "Spread"]
        """
        if not self.is_connected():
            logger.warning("Cannot fetch bars: not connected to MT5")
            return pd.DataFrame()

        tf = self._get_mt5_timeframe(timeframe)

        try:
            rates = None
            if date_from:
                d_to = date_to or datetime.now()
                rates = mt5.copy_rates_range(symbol, tf, date_from, d_to)
            else:
                rates = mt5.copy_rates_from_pos(symbol, tf, start_pos, count)

            if rates is None:
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"Failed to copy rates for {symbol} {timeframe}: {error_code} - {error_desc}"
                )
                return pd.DataFrame()

            # Create DataFrame from numpy array
            df = pd.DataFrame(rates)

            # Convert time to datetime
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Select and rename columns
            df = df[["time", "open", "high", "low", "close", "tick_volume", "spread"]]
            df.columns = [
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "spread",
            ]

            # Set index to Timestamp
            df.set_index("timestamp", inplace=True)

            if df is not None and not df.empty:
                logger.info(
                    f"Data for {symbol} {timeframe} from {df.index[0]} to {df.index[-1]} fetched successfully"
                )
            else:
                logger.warning(f"No data for {symbol} {timeframe}")

            return df

        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return pd.DataFrame()

    def get_ticks(
        self,
        symbol: str,
        count: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        flags: int = mt5.COPY_TICKS_ALL,
        as_dataframe: bool = True,
    ) -> Union[pd.DataFrame, List[Dict[str, Any]], None]:
        """
        Get ticks from MT5.

        Args:
            symbol: Trading symbol
            count: Number of ticks to retrieve
            start: Start date/time
            end: End date/time
            flags: Tick flags (COPY_TICKS_ALL, COPY_TICKS_INFO, COPY_TICKS_TRADE)
            as_dataframe: Return as DataFrame (True) or list of dicts (False)

        Returns:
            DataFrame or list of dicts containing tick data, or None on error
        """
        if not self.is_connected():
            logger.warning("Cannot fetch ticks: not connected to MT5")
            return None

        try:
            ticks = None
            if start and end:
                # Range based
                ticks = mt5.copy_ticks_range(symbol, start, end, flags)
            elif start:
                # From date based
                ticks = mt5.copy_ticks_from(symbol, start, count, flags)
            else:
                # Recent ticks (using now as base)
                # Note: copy_ticks_from retrieves ticks with time LESS than date_from
                ticks = mt5.copy_ticks_from(symbol, datetime.now(), count, flags)

            if ticks is None:
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"Failed to copy ticks for {symbol}: {error_code} - {error_desc}"
                )
                return None

            # Handle as valid result (even if empty list/array)
            if len(ticks) == 0:
                return pd.DataFrame() if as_dataframe else []

            if as_dataframe:
                df = pd.DataFrame(ticks)
                df["time"] = pd.to_datetime(df["time"], unit="s")

                # Filter unwanted columns
                cols_to_drop = ["last", "volume", "time_msc", "flags", "volume_real"]
                df.drop(
                    columns=[c for c in cols_to_drop if c in df.columns], inplace=True
                )

                # Rename columns
                df.rename(
                    columns={"ask": "ask", "bid": "bid", "time": "timestamp"},
                    inplace=True,
                )

                df.set_index("timestamp", inplace=True)
                logger.info(
                    f"Data for {symbol} ticks from {df.index[0]} to {df.index[-1]} fetched successfully"
                )
                return df
            else:
                # Convert numpy records to dicts
                return [dict(zip(ticks.dtype.names, x)) for x in ticks]

        except Exception as e:
            logger.error(f"Error fetching ticks for {symbol}: {e}")
            return None

    # =============================================================================
    # STREAMING
    # =============================================================================

    def start_streaming(
        self,
        symbol: str,
        data_type: str,
        callback: Callable[[Any], None],
        interval: float = 1.0,
        timeframe: Optional[str] = None,
    ) -> bool:
        """
        Start streaming real-time data.

        Args:
            symbol: Trading symbol
            data_type: Type of data to stream ("ticks" or "bars")
            callback: Function to call with new data
            interval: Update interval in seconds (for bars)
            timeframe: Timeframe for bars (required if data_type="bars")

        Returns:
            True if streaming started successfully, False otherwise
        """
        if not self.is_connected():
            logger.warning("Cannot start streaming: not connected to MT5")
            return False

        if data_type == "bars" and not timeframe:
            logger.error("Timeframe required for bar streaming")
            return False

        stream_id = f"{symbol}_{data_type}"
        if self._active_streams.get(stream_id):
            logger.warning(f"Stream already active for {stream_id}")
            return True

        self._active_streams[stream_id] = True
        thread = threading.Thread(
            target=self._stream_worker,
            args=(symbol, data_type, callback, interval, timeframe),
            name=f"MT5Stream_{stream_id}",
            daemon=True,
        )
        self._stream_threads[stream_id] = thread
        thread.start()
        logger.info(f"Started streaming {data_type} for {symbol}")
        return True

    def stop_streaming(self, symbol: str, data_type: str) -> bool:
        """
        Stop streaming data for a symbol.

        Args:
            symbol: Trading symbol
            data_type: Type of data being streamed

        Returns:
            True if stopped successfully, False otherwise
        """
        stream_id = f"{symbol}_{data_type}"
        if not self._active_streams.get(stream_id):
            logger.warning(f"No active stream for {stream_id}")
            return False

        self._active_streams[stream_id] = False
        # Remove from threads dict immediately, though thread might take a moment to die
        if stream_id in self._stream_threads:
            del self._stream_threads[stream_id]

        logger.info(f"Stopped streaming {data_type} for {symbol}")
        return True

    def _stream_worker(  # noqa: C901
        self,
        symbol: str,
        data_type: str,
        callback: Callable[[Any], None],
        interval: float,
        timeframe: Optional[str],
    ) -> None:
        """Worker thread for streaming data."""
        stream_id = f"{symbol}_{data_type}"
        last_data = None

        logger.debug(f"Stream worker started for {stream_id}")

        while self._active_streams.get(stream_id):
            try:
                current_data = None
                if data_type == "ticks":
                    # Get latest tick
                    ticks = self.get_ticks(symbol, count=1, as_dataframe=False)
                    if ticks and len(ticks) > 0:
                        # ticks is a list of dicts, get first (and only) element
                        # Copy to avoid modifying original list item if reused (though list is fresh)
                        current_data = ticks[0].copy()
                        current_data["symbol"] = symbol

                        # For ticks, we only callback if something changed (e.g. time or price)
                        # A simple equality check on the dict works
                        # Note: we compare BEFORE injecting symbol for purity, but ticks[0] is fresh.
                        if last_data is None or current_data != last_data:
                            callback(current_data)
                            last_data = current_data

                    time.sleep(0.1)  # 100ms polling for ticks

                elif data_type == "bars":
                    # Get latest bar
                    if timeframe:
                        df = self.get_bars(symbol, timeframe, count=1)
                        if not df.empty:
                            # Convert last row to Series
                            current_data = df.iloc[-1].copy()
                            # Inject symbol (will likely cast Series to object dtype if it was float/int)
                            current_data["symbol"] = symbol

                            # Note: equals check might fail if types changed due to injection.
                            # But we compare against last_data which also has symbol injected.
                            if last_data is None or not current_data.equals(last_data):
                                callback(current_data)
                                last_data = current_data

                    time.sleep(interval)

            except Exception as e:
                logger.error(f"Error in stream worker for {stream_id}: {e}")
                time.sleep(1)  # Backoff on error

        logger.debug(f"Stream worker finished for {stream_id}")

    def __repr__(self) -> str:
        """Return string representation of the client."""
        return (
            f"MT5Client(state={self.connection_state}, "
            f"account={self.account_login}, server={self.account_server})"
        )

    def __str__(self) -> str:
        """Return user-friendly string representation."""
        return f"MT5Client [{self.connection_state}]"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures proper cleanup."""
        self.shutdown()


# Export the client class
__all__ = ["MT5Client"]

