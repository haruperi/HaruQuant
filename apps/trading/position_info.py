"""
PositionInfo class for accessing position information.

This module provides a platform-agnostic implementation of position information
access, inspired by MT5's PositionInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from apps.logger import logger


class PositionType(Enum):
    """Position type enumeration."""

    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class PositionDataProvider(Protocol):
    """
    Protocol for position data providers.

    Any trading platform adapter should implement this protocol
    to provide position information to the PositionInfo class.
    """

    def get_ticket(self) -> int:
        """Get position ticket/ID."""
        ...

    def get_time(self) -> datetime:
        """Get position open time."""
        ...

    def get_time_msc(self) -> int:
        """Get position open time in milliseconds."""
        ...

    def get_time_update(self) -> datetime:
        """Get position last update time."""
        ...

    def get_time_update_msc(self) -> int:
        """Get position last update time in milliseconds."""
        ...

    def get_position_type(self) -> PositionType:
        """Get position type (buy/sell)."""
        ...

    def get_magic(self) -> int:
        """Get magic number."""
        ...

    def get_identifier(self) -> int:
        """Get position identifier."""
        ...

    def get_volume(self) -> float:
        """Get position volume."""
        ...

    def get_price_open(self) -> float:
        """Get position open price."""
        ...

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        ...

    def get_take_profit(self) -> float:
        """Get take profit price."""
        ...

    def get_price_current(self) -> float:
        """Get current market price."""
        ...

    def get_swap(self) -> float:
        """Get accumulated swap."""
        ...

    def get_profit(self) -> float:
        """Get current profit/loss."""
        ...

    def get_symbol(self) -> str:
        """Get position symbol."""
        ...

    def get_comment(self) -> str:
        """Get position comment."""
        ...

    def select_position(self, symbol: str) -> bool:
        """Select position by symbol."""
        ...

    def select_by_magic(self, symbol: str, magic: int) -> bool:
        """Select position by symbol and magic number."""
        ...

    def select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        ...

    def select_by_index(self, index: int) -> bool:
        """Select position by index."""
        ...

    def get_total_positions(self) -> int:
        """Get total number of open positions."""
        ...

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits for price formatting."""
        ...

    def get_margin_mode(self) -> str:
        """Get account margin mode."""
        ...


class MT5PositionProvider:
    """
    Implementation of PositionDataProvider using MT5Client.

    This class adapts an MT5Client instance to the PositionDataProvider protocol,
    providing access to live position data from MT5.
    """

    def __init__(self, mt5_client):
        """
        Initialize MT5PositionProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
        """
        self._client = mt5_client
        self._positions: List[Dict[str, Any]] = []
        self._current_index = -1
        self._refresh_positions()

    def _refresh_positions(self) -> None:
        """Refresh positions from MT5."""
        positions = self._client.get_positions()
        if positions:
            self._positions = positions
            if self._positions and self._current_index == -1:
                self._current_index = 0
        else:
            self._positions = []
            self._current_index = -1

    def _get_current(self) -> Dict[str, Any]:
        """Get current position data."""
        if 0 <= self._current_index < len(self._positions):
            return self._positions[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get position ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_time(self) -> datetime:
        """Get position open time."""
        return datetime.fromtimestamp(int(self._get_current().get("time", 0)))

    def get_time_msc(self) -> int:
        """Get position open time in milliseconds."""
        return int(self._get_current().get("time_msc", 0))

    def get_time_update(self) -> datetime:
        """Get position last update time."""
        return datetime.fromtimestamp(int(self._get_current().get("time_update", 0)))

    def get_time_update_msc(self) -> int:
        """Get position last update time in milliseconds."""
        return int(self._get_current().get("time_update_msc", 0))

    def get_position_type(self) -> PositionType:
        """Get position type."""
        type_int = self._get_current().get("type", -1)
        if type_int == 0:
            return PositionType.BUY
        elif type_int == 1:
            return PositionType.SELL
        return PositionType.UNKNOWN

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_identifier(self) -> int:
        """Get position identifier."""
        return int(self._get_current().get("identifier", 0))

    def get_volume(self) -> float:
        """Get position volume."""
        return float(self._get_current().get("volume", 0.0))

    def get_price_open(self) -> float:
        """Get position open price."""
        return float(self._get_current().get("price_open", 0.0))

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        return float(self._get_current().get("sl", 0.0))

    def get_take_profit(self) -> float:
        """Get take profit price."""
        return float(self._get_current().get("tp", 0.0))

    def get_price_current(self) -> float:
        """Get current market price."""
        return float(self._get_current().get("price_current", 0.0))

    def get_swap(self) -> float:
        """Get accumulated swap."""
        return float(self._get_current().get("swap", 0.0))

    def get_profit(self) -> float:
        """Get current profit/loss."""
        return float(self._get_current().get("profit", 0.0))

    def get_symbol(self) -> str:
        """Get position symbol."""
        return str(self._get_current().get("symbol", ""))

    def get_comment(self) -> str:
        """Get position comment."""
        return str(self._get_current().get("comment", ""))

    def select_position(self, symbol: str) -> bool:
        """Select position by symbol."""
        for i, pos in enumerate(self._positions):
            if pos.get("symbol") == symbol:
                self._current_index = i
                return True
        return False

    def select_by_magic(self, symbol: str, magic: int) -> bool:
        """Select position by symbol and magic number."""
        for i, pos in enumerate(self._positions):
            if pos.get("symbol") == symbol and pos.get("magic") == magic:
                self._current_index = i
                return True
        return False

    def select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        for i, pos in enumerate(self._positions):
            if pos.get("ticket") == ticket:
                self._current_index = i
                return True
        return False

    def select_by_index(self, index: int) -> bool:
        """Select position by index."""
        if 0 <= index < len(self._positions):
            self._current_index = index
            return True
        return False

    def get_total_positions(self) -> int:
        """Get total number of positions."""
        return len(self._positions)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits from MT5."""
        symbol_info = self._client.get_symbol_info(symbol)
        if symbol_info:
            return int(symbol_info.get("digits", 5))
        return 5

    def get_margin_mode(self) -> str:
        """Get account margin mode from MT5."""
        account_info = self._client.get_account_info()
        if account_info:
            margin_mode = account_info.get("margin_mode", 0)
            if margin_mode == 2:
                return "hedging"
            return "netting"
        return "hedging"


class BacktestPositionProvider:
    """
    Implementation of PositionDataProvider for backtesting.

    This class simulates position data for backtesting without requiring
    an MT5 connection. Positions can be added, updated, and removed programmatically.
    """

    def __init__(self, margin_mode: str = "hedging", default_digits: int = 5):
        """
        Initialize BacktestPositionProvider.

        Args:
            margin_mode: Account margin mode ("hedging" or "netting")
            default_digits: Default number of digits for price formatting
        """
        self._positions: List[Dict[str, Any]] = []
        self._current_index = -1
        self._margin_mode = margin_mode
        self._default_digits = default_digits
        self._next_ticket = 1000000  # Start ticket numbers from 1000000

    def add_position(
        self,
        symbol: str,
        position_type: PositionType,
        volume: float,
        price_open: float,
        price_current: float = 0.0,
        magic: int = 0,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        comment: str = "",
        ticket: Optional[int] = None,
        time: Optional[datetime] = None,
    ) -> int:
        """
        Add a simulated position.

        Args:
            symbol: Trading symbol
            position_type: Position type (BUY or SELL)
            volume: Position volume in lots
            price_open: Opening price
            price_current: Current market price
            magic: Magic number
            stop_loss: Stop loss price
            take_profit: Take profit price
            comment: Position comment
            ticket: Optional ticket number (auto-generated if not provided)
            time: Optional position open time (defaults to now)

        Returns:
            Position ticket number
        """
        if ticket is None:
            ticket = self._next_ticket
            self._next_ticket += 1
        else:
            # Update next ticket if provided ticket is higher
            if ticket >= self._next_ticket:
                self._next_ticket = ticket + 1

        if time is None:
            time = datetime.now()

        # Calculate profit (simplified)
        if position_type == PositionType.BUY:
            profit = (price_current - price_open) * volume * 100000  # Simplified
        elif position_type == PositionType.SELL:
            profit = (price_open - price_current) * volume * 100000
        else:
            profit = 0.0

        position_data = {
            "ticket": ticket,
            "time": int(time.timestamp()),
            "time_msc": int(time.timestamp() * 1000),
            "time_update": int(time.timestamp()),
            "time_update_msc": int(time.timestamp() * 1000),
            "type": 0 if position_type == PositionType.BUY else 1,
            "magic": magic,
            "identifier": ticket,
            "volume": volume,
            "price_open": price_open,
            "sl": stop_loss,
            "tp": take_profit,
            "price_current": price_current,
            "swap": 0.0,
            "profit": profit,
            "symbol": symbol,
            "comment": comment,
        }

        self._positions.append(position_data)

        # Auto-select the newly added position
        if self._current_index == -1:
            self._current_index = 0

        logger.debug(
            f"Added backtest position: {symbol} {position_type.value} {volume} lots, ticket {ticket}"
        )
        return ticket

    def update_position(
        self,
        ticket: int,
        price_current: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """
        Update an existing position.

        Args:
            ticket: Position ticket to update
            price_current: New current price
            stop_loss: New stop loss
            take_profit: New take profit

        Returns:
            True if position was found and updated
        """
        for pos in self._positions:
            if pos["ticket"] == ticket:
                if price_current is not None:
                    pos["price_current"] = price_current
                    # Recalculate profit
                    position_type = (
                        PositionType.BUY if pos["type"] == 0 else PositionType.SELL
                    )
                    if position_type == PositionType.BUY:
                        pos["profit"] = (
                            (price_current - pos["price_open"]) * pos["volume"] * 100000
                        )
                    else:
                        pos["profit"] = (
                            (pos["price_open"] - price_current) * pos["volume"] * 100000
                        )

                if stop_loss is not None:
                    pos["sl"] = stop_loss

                if take_profit is not None:
                    pos["tp"] = take_profit

                pos["time_update"] = int(datetime.now().timestamp())
                pos["time_update_msc"] = int(datetime.now().timestamp() * 1000)

                return True
        return False

    def remove_position(self, ticket: int) -> bool:
        """
        Remove a position by ticket.

        Args:
            ticket: Position ticket to remove

        Returns:
            True if position was found and removed
        """
        for i, pos in enumerate(self._positions):
            if pos["ticket"] == ticket:
                self._positions.pop(i)
                # Adjust current index if needed
                if self._current_index >= len(self._positions):
                    self._current_index = len(self._positions) - 1
                logger.debug(f"Removed backtest position ticket {ticket}")
                return True
        return False

    def clear_positions(self) -> None:
        """Remove all positions."""
        self._positions.clear()
        self._current_index = -1
        logger.debug("Cleared all backtest positions")

    def _get_current(self) -> Dict[str, Any]:
        """Get current position data."""
        if 0 <= self._current_index < len(self._positions):
            return self._positions[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get position ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_time(self) -> datetime:
        """Get position open time."""
        return datetime.fromtimestamp(self._get_current().get("time", 0))

    def get_time_msc(self) -> int:
        """Get position open time in milliseconds."""
        return int(self._get_current().get("time_msc", 0))

    def get_time_update(self) -> datetime:
        """Get position last update time."""
        return datetime.fromtimestamp(self._get_current().get("time_update", 0))

    def get_time_update_msc(self) -> int:
        """Get position last update time in milliseconds."""
        return int(self._get_current().get("time_update_msc", 0))

    def get_position_type(self) -> PositionType:
        """Get position type."""
        type_int = self._get_current().get("type", -1)
        if type_int == 0:
            return PositionType.BUY
        elif type_int == 1:
            return PositionType.SELL
        return PositionType.UNKNOWN

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_identifier(self) -> int:
        """Get position identifier."""
        return int(self._get_current().get("identifier", 0))

    def get_volume(self) -> float:
        """Get position volume."""
        return float(self._get_current().get("volume", 0.0))

    def get_price_open(self) -> float:
        """Get open price."""
        return float(self._get_current().get("price_open", 0.0))

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        return float(self._get_current().get("sl", 0.0))

    def get_take_profit(self) -> float:
        """Get take profit price."""
        return float(self._get_current().get("tp", 0.0))

    def get_price_current(self) -> float:
        """Get current price."""
        return float(self._get_current().get("price_current", 0.0))

    def get_swap(self) -> float:
        """Get swap."""
        return float(self._get_current().get("swap", 0.0))

    def get_profit(self) -> float:
        """Get profit."""
        return float(self._get_current().get("profit", 0.0))

    def get_symbol(self) -> str:
        """Get symbol name."""
        return str(self._get_current().get("symbol", ""))

    def get_comment(self) -> str:
        """Get position comment."""
        return str(self._get_current().get("comment", ""))

    def select_position(self, symbol: str) -> bool:
        """Select position by symbol."""
        for i, pos in enumerate(self._positions):
            if pos.get("symbol") == symbol:
                self._current_index = i
                return True
        return False

    def select_by_magic(self, symbol: str, magic: int) -> bool:
        """Select position by symbol and magic number."""
        for i, pos in enumerate(self._positions):
            if pos.get("symbol") == symbol and pos.get("magic") == magic:
                self._current_index = i
                return True
        return False

    def select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        for i, pos in enumerate(self._positions):
            if pos.get("ticket") == ticket:
                self._current_index = i
                return True
        return False

    def select_by_index(self, index: int) -> bool:
        """Select position by index."""
        if 0 <= index < len(self._positions):
            self._current_index = index
            return True
        return False

    def get_total_positions(self) -> int:
        """Get total number of positions."""
        return len(self._positions)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits (uses default)."""
        return self._default_digits

    def get_margin_mode(self) -> str:
        """Get account margin mode."""
        return self._margin_mode


class PositionInfo:
    """
    Class for accessing position information.

    This class provides a clean interface to position information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import PositionInfo, MT5PositionProvider

        client = MT5Client()
        client.initialize()
        provider = MT5PositionProvider(client)
        position = PositionInfo(provider)

        # Select and display position
        if position.select("EURUSD"):
            print(f"Ticket: {position.ticket()}")
            print(f"Type: {position.type_description()}")
            print(f"Volume: {position.volume()}")
            print(f"Profit: {position.profit()}")
    """

    def __init__(self, data_provider: PositionDataProvider):
        """
        Initialize PositionInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          PositionDataProvider protocol.
                          Use MT5PositionProvider for live trading.
        """
        self._provider = data_provider

        # State storage for CheckState functionality
        self._stored_type: Optional[PositionType] = None
        self._stored_volume: float = 0.0
        self._stored_price: float = 0.0
        self._stored_stop_loss: float = 0.0
        self._stored_take_profit: float = 0.0

    def total_positions(self) -> int:
        """
        Get total number of open positions.

        Returns:
            Total count of positions.
        """
        return self._provider.get_total_positions()

    def ticket(self) -> int:
        """
        Get position ticket/ID.

        Returns:
            Position ticket number.
        """
        return self._provider.get_ticket()

    def time(self) -> datetime:
        """
        Get position open time.

        Returns:
            Position open datetime.
        """
        return self._provider.get_time()

    def time_msc(self) -> int:
        """
        Get position open time in milliseconds.

        Returns:
            Position open time in milliseconds since epoch.
        """
        return self._provider.get_time_msc()

    def time_update(self) -> datetime:
        """
        Get position last update time.

        Returns:
            Position last update datetime.
        """
        return self._provider.get_time_update()

    def time_update_msc(self) -> int:
        """
        Get position last update time in milliseconds.

        Returns:
            Position last update time in milliseconds since epoch.
        """
        return self._provider.get_time_update_msc()

    def position_type(self) -> PositionType:
        """
        Get position type.

        Returns:
            PositionType enum value (BUY or SELL).
        """
        return self._provider.get_position_type()

    def type_description(self) -> str:
        """
        Get position type as a descriptive string.

        Returns:
            Human-readable description of position type.
        """
        return self.format_type(self.position_type())

    def magic(self) -> int:
        """
        Get magic number.

        Returns:
            Magic number used to identify the position.
        """
        return self._provider.get_magic()

    def identifier(self) -> int:
        """
        Get position identifier.

        Returns:
            Position identifier (unique across all positions).
        """
        return self._provider.get_identifier()

    # Fast access methods to double position properties

    def volume(self) -> float:
        """
        Get position volume.

        Returns:
            Position volume in lots.
        """
        return self._provider.get_volume()

    def price_open(self) -> float:
        """
        Get position open price.

        Returns:
            Price at which position was opened.
        """
        return self._provider.get_price_open()

    def stop_loss(self) -> float:
        """
        Get stop loss price.

        Returns:
            Stop loss price (0.0 if not set).
        """
        return self._provider.get_stop_loss()

    def take_profit(self) -> float:
        """
        Get take profit price.

        Returns:
            Take profit price (0.0 if not set).
        """
        return self._provider.get_take_profit()

    def price_current(self) -> float:
        """
        Get current market price.

        Returns:
            Current market price for the position's symbol.
        """
        return self._provider.get_price_current()

    def commission(self) -> float:
        """
        Get position commission.

        Note: This property is deprecated in MT5 and returns 0.0.
        Commission information should be retrieved from deals instead.

        Returns:
            Always returns 0.0 (deprecated).
        """
        # Property POSITION_COMMISSION is deprecated in MT5
        logger.warning("commission() is deprecated. Use deal history instead.")
        return 0.0

    def swap(self) -> float:
        """
        Get accumulated swap.

        Returns:
            Accumulated swap/rollover charges.
        """
        return self._provider.get_swap()

    def profit(self) -> float:
        """
        Get current profit/loss.

        Returns:
            Current profit (positive) or loss (negative).
        """
        return self._provider.get_profit()

    # Fast access methods to string position properties

    def symbol(self) -> str:
        """
        Get position symbol.

        Returns:
            Trading symbol (e.g., "EURUSD").
        """
        return self._provider.get_symbol()

    def comment(self) -> str:
        """
        Get position comment.

        Returns:
            Position comment string.
        """
        return self._provider.get_comment()

    # Info methods

    @staticmethod
    def format_type(position_type: PositionType) -> str:
        """
        Convert position type to text.

        Args:
            position_type: PositionType enum value.

        Returns:
            Human-readable position type string.
        """
        if position_type == PositionType.BUY:
            return "buy"
        elif position_type == PositionType.SELL:
            return "sell"
        return "unknown"

    # Selection methods

    def select_position(self, symbol: str) -> bool:
        """
        Select position by symbol.

        Args:
            symbol: Symbol to select.

        Returns:
            True if position found and selected.
        """
        return self._provider.select_position(symbol)

    def select(self, symbol: str) -> bool:
        """Alias for select_position."""
        return self.select_position(symbol)

    def select_by_ticket(self, ticket: int) -> bool:
        """
        Select position by ticket.

        Args:
            ticket: Ticket number.

        Returns:
            True if position found and selected.
        """
        return self._provider.select_by_ticket(ticket)

    def select_by_magic(self, symbol: str, magic: int) -> bool:
        """
        Select position by symbol and magic number.

        Args:
            symbol: Symbol name.
            magic: Magic number.

        Returns:
            True if position found and selected.
        """
        return self._provider.select_by_magic(symbol, magic)

    def select_by_index(self, index: int) -> bool:
        """
        Select position by index.

        Args:
            index: Position index (0 to total-1).

        Returns:
            True if position found and selected.
        """
        return self._provider.select_by_index(index)

    def format_position(self) -> str:
        """
        Format position parameters as text.

        Returns:
            Formatted string describing the position.
        """
        symbol_name = self.symbol()
        digits = self._provider.get_symbol_digits(symbol_name)
        margin_mode = self._provider.get_margin_mode()

        # Get position type description
        type_desc = self.type_description()

        # Format based on margin mode
        if margin_mode == "hedging":
            # In hedging mode, show ticket number
            result = (
                f"#{self.ticket()} {type_desc} "
                f"{self.volume():.2f} {symbol_name} "
                f"{self.price_open():.{digits + 3}f}"
            )
        else:
            # In netting mode, no ticket number
            result = (
                f"{type_desc} {self.volume():.2f} "
                f"{symbol_name} {self.price_open():.{digits + 3}f}"
            )

        # Add stop loss if set
        sl = self.stop_loss()
        if sl != 0.0:
            result += f" sl: {sl:.{digits}f}"

        # Add take profit if set
        tp = self.take_profit()
        if tp != 0.0:
            result += f" tp: {tp:.{digits}f}"

        return result

    # State management methods

    def store_state(self) -> None:
        """
        Store current position state.

        Saves the current position's type, volume, price, stop loss,
        and take profit for later comparison with check_state().
        """
        self._stored_type = self.position_type()
        self._stored_volume = self.volume()
        self._stored_price = self.price_open()
        self._stored_stop_loss = self.stop_loss()
        self._stored_take_profit = self.take_profit()

    def check_state(self) -> bool:
        """
        Check if position state has changed.

        Compares current position state with the state stored by
        store_state().

        Returns:
            True if position has changed, False if unchanged.
        """
        if self._stored_type is None:
            # No state stored yet
            return True

        if (
            self._stored_type == self.position_type()
            and self._stored_volume == self.volume()
            and self._stored_price == self.price_open()
            and self._stored_stop_loss == self.stop_loss()
            and self._stored_take_profit == self.take_profit()
        ):
            return False

        return True

    def __repr__(self) -> str:
        """Return string representation of PositionInfo."""
        try:
            return (
                f"PositionInfo(ticket={self.ticket()}, "
                f"symbol={self.symbol()}, "
                f"type={self.position_type().value}, "
                f"volume={self.volume():.2f}, "
                f"profit={self.profit():.2f})"
            )
        except Exception:
            return "PositionInfo(no position selected)"
