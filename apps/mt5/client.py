"""
MT5 Trading System - Client Module.

This module provides the main client class for connecting to and interacting with
the MetaTrader 5 terminal. It handles connection management, authentication,
auto-reconnection, multi-account support, and event handling.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import MetaTrader5 as mt5
import pandas as pd

from apps.logger import logger


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
        >>> client = MT5Client()
        >>> client.initialize(login=12345, password="pass", server="Server-Demo")
        >>> if client.is_connected():
        ...     print("Connected successfully")
        >>> client.shutdown()
    """

    def __init__(
        self,
        path: str = "",
        login: int = 0,
        password: str = "",
        server: str = "",
        timeout: int = 60000,
        portable: bool = False,
    ):
        """
        Initialize the MT5Client instance.

        Args:
            path: Path to MT5 terminal executable
            login: Account login number
            password: Account password
            server: MT5 server name
            timeout: Connection timeout in milliseconds (default: 60000)
            portable: Whether to use portable mode (default: False)

        Example:
            >>> client = MT5Client(
            ...     path="C:/Program Files/MT5/terminal64.exe",
            ...     login=12345,
            ...     password="pass",
            ...     server="Server-Demo",
            ...     timeout=30000,
            ...     portable=False
            ... )
        """
        logger.info("Initializing MT5Client")

        # Connection attributes
        self.connection_state: ConnectionState = ConnectionState.DISCONNECTED
        self.timeout: int = timeout
        self.portable: bool = portable

        # Authentication attributes
        self.account_login: int = login
        self.account_password: str = password
        self.account_server: str = server
        self.path: str = path

        # Auto-reconnection attributes
        self.auto_reconnect_enabled: bool = False
        self.retry_attempts: int = 3
        self.retry_delay: int = 5
        self._reconnection_in_progress: bool = False

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

        # Cached info data
        self.account_info: Optional[Dict[str, Any]] = None
        self.terminal_info: Optional[Dict[str, Any]] = None
        self._symbol_info_cache: Dict[str, Dict[str, Any]] = {}

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

        self.initialize()

        if self.connection_state == ConnectionState.CONNECTED:
            logger.success("MT5Client initialized successfully")
        else:
            logger.warning("MT5Client initialization incomplete")

        # =============================================================================
        # CONNECTION MANAGEMENT
        # =============================================================================

    def initialize(self) -> bool:
        """
        Initialize connection to MT5 terminal and login to trading account.

        Returns:
            True if initialization and login successful, False otherwise
        """
        logger.info("Initializing MT5 terminal connection")
        self.connection_state = ConnectionState.INITIALIZING
        self._connection_attempts += 1

        try:
            # 1. Start MT5 terminal
            logger.debug(f"Starting MT5 terminal from {self.path}")
            if not mt5.initialize(
                path=self.path, timeout=self.timeout, portable=self.portable
            ):
                error_code, error_desc = mt5.last_error()
                logger.error(
                    f"MT5 terminal initialization failed: {error_code} - {error_desc}"
                )
                self.connection_state = ConnectionState.FAILED
                self._failed_connections += 1
                return False

            # 2. Login to trading account
            logger.debug(
                f"Logging in to account {self.account_login} on server {self.account_server}"
            )
            if not mt5.login(
                login=self.account_login,
                password=self.account_password,
                server=self.account_server,
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
            logger.info(
                f"Successfully logged in: account={self.account_login}, server={self.account_server}"
            )
            return True

        except Exception as e:
            logger.error(f"MT5Client.initialize: {e}")
            self.connection_state = ConnectionState.FAILED
            self._failed_connections += 1
            return False

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
        # Check both our state and MT5's terminal info
        terminal_info = mt5.terminal_info()
        is_mt5_connected = terminal_info is not None and terminal_info.connected

        is_our_state_connected = self.connection_state == ConnectionState.CONNECTED

        # Update our state if there's a mismatch
        if is_our_state_connected and not is_mt5_connected:
            logger.warning("Connection state mismatch detected - updating state")
            self.connection_state = ConnectionState.DISCONNECTED

            # Attempt auto-reconnection if enabled
            if self.auto_reconnect_enabled and not self._reconnection_in_progress:
                logger.info("Initiating auto-reconnection")
                self._handle_reconnection()

        return is_mt5_connected and is_our_state_connected

    def shutdown(self) -> None:
        """
        Shutdown the MT5 terminal connection and clean up resources.

        This method should be called when you're done using the client to
        properly close the connection and release resources.

        Example:
            >>> client = MT5Client()
            >>> client.initialize()
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
    # AUTO-RECONNECTION
    # =============================================================================

    def reconnect(self) -> bool:
        """
        Attempt to reconnect to MT5 terminal.

        Uses stored credentials to reconnect. If no credentials are stored,
        returns False.

        Returns:
            bool: True if reconnection successful, False otherwise

        Example:
            >>> if not client.is_connected():
            ...     client.reconnect()
        """
        logger.info("Attempting reconnection to MT5 terminal")
        self.connection_state = ConnectionState.RECONNECTING

        if not (self.account_login and self.account_password and self.account_server):
            logger.error("Cannot reconnect: no credentials stored")
            return False

        # Shutdown existing connection
        try:
            mt5.shutdown()
        except Exception as e:
            logger.debug(f"Exception during shutdown before reconnect: {e}")

        # Wait a moment before reconnecting
        time.sleep(1)

        # Attempt to reinitialize and login
        success = self.initialize()

        if success:
            logger.success("Reconnection successful")
        else:
            logger.error("Reconnection failed")
            self.connection_state = ConnectionState.FAILED

        return success

    def _handle_reconnection(self) -> bool:
        """
        Handle automatic reconnection logic.

        Returns:
            bool: True if reconnection successful
        """
        if self._reconnection_in_progress:
            return False

        self._reconnection_in_progress = True
        logger.info("Starting auto-reconnection process")

        for attempt in range(1, self.retry_attempts + 1):
            logger.info(f"Reconnection attempt {attempt}/{self.retry_attempts}")

            if self.reconnect():
                self._reconnection_in_progress = False
                logger.success("Auto-reconnection successful")
                return True

            if attempt < self.retry_attempts:
                logger.info(f"Waiting {self.retry_delay} seconds before next attempt")
                time.sleep(self.retry_delay)

        self._reconnection_in_progress = False
        logger.error("Auto-reconnection failed after all attempts")
        return False

    # =============================================================================
    # INFO DATA METHODS
    # =============================================================================

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information from MT5 and cache it.

        Returns:
            Dictionary with account information or None if failed

        Example:
            >>> client.get_account_info()
            >>> print(client.account_info['balance'])
        """
        if not self.is_connected():
            logger.warning("Cannot fetch account info: not connected to MT5")
            return None

        account_info = mt5.account_info()
        if account_info is None:
            error_code, error_desc = mt5.last_error()
            logger.error(f"Failed to get account info: {error_code} - {error_desc}")
            return None

        self.account_info = account_info._asdict()
        logger.info("Account info fetched and cached")

        return self.account_info

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """
        Get terminal information from MT5 and cache it.

        Returns:
            Dictionary with terminal information or None if failed

        Example:
            >>> client.get_terminal_info()
            >>> print(client.terminal_info['build'])
        """
        if not self.is_connected():
            logger.warning("Cannot fetch terminal info: not connected to MT5")
            return None

        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            error_code, error_desc = mt5.last_error()
            logger.error(f"Failed to get terminal info: {error_code} - {error_desc}")
            return None

        # Convert to dictionary
        self.terminal_info = terminal_info._asdict()

        logger.info("Terminal info fetched and cached")
        return self.terminal_info

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information from MT5 and cache it.

        Args:
            symbol: Symbol name (e.g., "EURUSD")

        Returns:
            Dictionary with symbol information or None if failed

        Example:
            >>> client.get_symbol_info("EURUSD")
            >>> print(client._symbol_info_cache['EURUSD']['bid'])
        """
        if not self.is_connected():
            logger.warning("Cannot fetch symbol info: not connected to MT5")
            return None

        # Try to select symbol first
        mt5.symbol_select(symbol, True)

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error_code, error_desc = mt5.last_error()
            logger.error(
                f"Failed to get symbol info for {symbol}: {error_code} - {error_desc}"
            )
            return None

        # Cache the symbol info
        self._symbol_info_cache[symbol] = symbol_info._asdict()

        logger.info(f"Symbol info for {symbol} fetched and cached")
        return dict(symbol_info._asdict())

    def get_positions(
        self,
        symbol: Optional[str] = None,
        group: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get positions from MT5.

        Args:
            symbol: Filter by symbol
            group: Filter by group
            ticket: Filter by ticket

        Returns:
            List of dictionaries with position information
        """
        if not self.is_connected():
            logger.warning("Cannot fetch positions: not connected to MT5")
            return []

        try:
            if ticket:
                positions = mt5.positions_get(ticket=ticket)
            elif symbol:
                positions = mt5.positions_get(symbol=symbol)
            elif group:
                positions = mt5.positions_get(group=group)
            else:
                positions = mt5.positions_get()

            if positions is None:
                error_code, error_desc = mt5.last_error()
                # Error code 1 means "no suitable data found" (generic warning),
                # which is not an error for empty list
                if error_code != 1:
                    logger.debug(
                        f"mt5.positions_get returned None: {error_code} - {error_desc}"
                    )
                return []

            return [p._asdict() for p in positions]

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def get_orders(
        self,
        symbol: Optional[str] = None,
        group: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get active orders from MT5.

        Args:
            symbol: Filter by symbol
            group: Filter by group
            ticket: Filter by ticket

        Returns:
            List of dictionaries with order information
        """
        if not self.is_connected():
            logger.warning("Cannot fetch orders: not connected to MT5")
            return []

        try:
            if ticket:
                orders = mt5.orders_get(ticket=ticket)
            elif symbol:
                orders = mt5.orders_get(symbol=symbol)
            elif group:
                orders = mt5.orders_get(group=group)
            else:
                orders = mt5.orders_get()

            if orders is None:
                error_code, error_desc = mt5.last_error()
                if error_code != 1:
                    logger.debug(
                        f"mt5.orders_get returned None: {error_code} - {error_desc}"
                    )
                return []

            return [o._asdict() for o in orders]

        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def get_history_orders(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        group: Optional[str] = None,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get history orders from MT5.

        Args:
            date_from: Start date (required if ticket and position are None)
            date_to: End date (defaults to now)
            group: Filter by group
            ticket: Filter by order ticket
            position: Filter by position ticket

        Returns:
            List of dictionaries with history order information
        """
        if not self.is_connected():
            logger.warning("Cannot fetch history orders: not connected to MT5")
            return []

        try:
            if ticket:
                orders = mt5.history_orders_get(ticket=ticket)
            elif position:
                orders = mt5.history_orders_get(position=position)
            elif date_from:
                d_to = date_to or datetime.now()
                if group:
                    orders = mt5.history_orders_get(date_from, d_to, group=group)
                else:
                    orders = mt5.history_orders_get(date_from, d_to)
            else:
                # Default to last 30 days if nothing specified?
                # Or return empty? Better to require explicit range or id.
                # However, for ease of use, we might default to "all history" if user supplies "from=0"?
                # Let's assume user must provide one of them.
                logger.warning(
                    "Fetching history orders requires date_from, ticket, or position"
                )
                return []

            if orders is None:
                error_code, error_desc = mt5.last_error()
                if error_code != 1:
                    logger.debug(
                        f"mt5.history_orders_get returned None: {error_code} - {error_desc}"
                    )
                return []

            return [o._asdict() for o in orders]

        except Exception as e:
            logger.error(f"Error fetching history orders: {e}")
            return []

    def get_history_deals(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        group: Optional[str] = None,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch history deals from MT5.

        Args:
            date_from: Start date (required if ticket and position are None)
            date_to: End date (defaults to now)
            group: Filter by group
            ticket: Filter by ticket (order ticket usually)
            position: Filter by position ticket

        Returns:
            List of dictionaries with deal information
        """
        if not self.is_connected():
            logger.warning("Cannot fetch history deals: not connected to MT5")
            return []

        try:
            if ticket:
                deals = mt5.history_deals_get(ticket=ticket)
            elif position:
                deals = mt5.history_deals_get(position=position)
            elif date_from:
                d_to = date_to or datetime.now()
                if group:
                    deals = mt5.history_deals_get(date_from, d_to, group=group)
                else:
                    deals = mt5.history_deals_get(date_from, d_to)
            else:
                logger.warning(
                    "Fetching history deals requires date_from, ticket, or position"
                )
                return []

            if deals is None:
                error_code, error_desc = mt5.last_error()
                if error_code != 1:
                    logger.debug(
                        f"mt5.history_deals_get returned None: {error_code} - {error_desc}"
                    )
                return []

            return [d._asdict() for d in deals]

        except Exception as e:
            logger.error(f"Error fetching history deals: {e}")
            return []

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
                return df
            else:
                # Convert numpy records to dicts
                return [dict(zip(ticks.dtype.names, x)) for x in ticks]

        except Exception as e:
            logger.error(f"Error fetching ticks for {symbol}: {e}")
            return None

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
