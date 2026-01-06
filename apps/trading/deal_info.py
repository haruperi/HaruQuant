"""
DealInfo class for accessing historical deal information.

This module provides a platform-agnostic implementation of deal information
access, inspired by MT5's DealInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class DealType(Enum):
    """Deal type enumeration."""

    BUY = "buy"
    SELL = "sell"
    BALANCE = "balance"
    CREDIT = "credit"
    CHARGE = "charge"
    CORRECTION = "correction"
    BONUS = "bonus"
    COMMISSION = "commission"
    COMMISSION_DAILY = "commission_daily"
    COMMISSION_MONTHLY = "commission_monthly"
    COMMISSION_AGENT_DAILY = "commission_agent_daily"
    COMMISSION_AGENT_MONTHLY = "commission_agent_monthly"
    INTEREST = "interest"
    BUY_CANCELED = "buy_canceled"
    SELL_CANCELED = "sell_canceled"
    UNKNOWN = "unknown"


class DealEntry(Enum):
    """Deal entry direction enumeration."""

    IN = "in"  # Entry into position
    OUT = "out"  # Exit from position
    INOUT = "inout"  # Reversal (in and out simultaneously)
    OUT_BY = "out_by"  # Close by opposite position
    STATE = "state"  # State record (balance operations)
    UNKNOWN = "unknown"


class DealDataProvider(Protocol):
    """
    Protocol for deal data providers.

    Any trading platform adapter should implement this protocol
    to provide historical deal information to the DealInfo class.
    """

    def get_ticket(self) -> int:
        """Get deal ticket/ID."""
        ...

    def get_order(self) -> int:
        """Get order ticket that created this deal."""
        ...

    def get_time(self) -> datetime:
        """Get deal execution time."""
        ...

    def get_time_msc(self) -> int:
        """Get deal execution time in milliseconds."""
        ...

    def get_deal_type(self) -> DealType:
        """Get deal type."""
        ...

    def get_entry(self) -> DealEntry:
        """Get deal entry direction."""
        ...

    def get_magic(self) -> int:
        """Get magic number."""
        ...

    def get_position_id(self) -> int:
        """Get position ID."""
        ...

    def get_volume(self) -> float:
        """Get deal volume."""
        ...

    def get_price(self) -> float:
        """Get deal price."""
        ...

    def get_commission(self) -> float:
        """Get deal commission."""
        ...

    def get_swap(self) -> float:
        """Get deal swap."""
        ...

    def get_profit(self) -> float:
        """Get deal profit."""
        ...

    def get_symbol(self) -> str:
        """Get deal symbol."""
        ...

    def get_comment(self) -> str:
        """Get deal comment."""
        ...

    def get_external_id(self) -> str:
        """Get external deal ID."""
        ...

    def select_by_index(self, index: int) -> bool:
        """Select deal by index in history."""
        ...

    def get_total_deals(self) -> int:
        """Get total number of deals in history."""
        ...

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits for price formatting."""
        ...


class MT5DealProvider:
    """
    Implementation of DealDataProvider using MT5Client.

    This class adapts an MT5Client instance to the DealDataProvider protocol,
    providing access to historical deal data from MT5.
    """

    def __init__(self, mt5_client, date_from=None, date_to=None):
        """
        Initialize MT5DealProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
            date_from: Start date for deal history (datetime or None for all)
            date_to: End date for deal history (datetime or None for now)
        """
        self._client = mt5_client
        self._deals: List[Dict[str, Any]] = []
        self._current_index = -1
        self._refresh_deals(date_from, date_to)

    def _refresh_deals(self, date_from=None, date_to=None) -> None:
        """Refresh deals from MT5."""
        deals = self._client.fetch_history_deals(date_from=date_from, date_to=date_to)
        if deals:
            self._deals = deals
            if self._deals and self._current_index == -1:
                self._current_index = 0
        else:
            self._deals = []
            self._current_index = -1

    def _get_current(self) -> Dict[str, Any]:
        """Get current deal data."""
        if 0 <= self._current_index < len(self._deals):
            return self._deals[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get deal ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_order(self) -> int:
        """Get order ticket."""
        return int(self._get_current().get("order", 0))

    def get_time(self) -> datetime:
        """Get deal time."""
        return datetime.fromtimestamp(int(self._get_current().get("time", 0)))

    def get_time_msc(self) -> int:
        """Get deal time in milliseconds."""
        return int(self._get_current().get("time_msc", 0))

    def get_deal_type(self) -> DealType:
        """Get deal type."""
        val = int(self._get_current().get("type", -1))
        type_map = {
            0: DealType.BUY,
            1: DealType.SELL,
            2: DealType.BALANCE,
            3: DealType.CREDIT,
            4: DealType.CHARGE,
            5: DealType.CORRECTION,
            6: DealType.BONUS,
            7: DealType.COMMISSION,
            8: DealType.COMMISSION_DAILY,
            9: DealType.COMMISSION_MONTHLY,
            10: DealType.COMMISSION_AGENT_DAILY,
            11: DealType.COMMISSION_AGENT_MONTHLY,
            12: DealType.INTEREST,
            13: DealType.BUY_CANCELED,
            14: DealType.SELL_CANCELED,
        }
        return type_map.get(val, DealType.UNKNOWN)

    def get_entry(self) -> DealEntry:
        """Get deal entry."""
        val = int(self._get_current().get("entry", -1))
        entry_map = {
            0: DealEntry.IN,
            1: DealEntry.OUT,
            2: DealEntry.INOUT,
            3: DealEntry.OUT_BY,
        }
        return entry_map.get(val, DealEntry.UNKNOWN)

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_position_id(self) -> int:
        """Get position ID."""
        return int(self._get_current().get("position_id", 0))

    def get_volume(self) -> float:
        """Get deal volume."""
        return float(self._get_current().get("volume", 0.0))

    def get_price(self) -> float:
        """Get deal price."""
        return float(self._get_current().get("price", 0.0))

    def get_commission(self) -> float:
        """Get commission."""
        return float(self._get_current().get("commission", 0.0))

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
        """Get deal comment."""
        return str(self._get_current().get("comment", ""))

    def get_external_id(self) -> str:
        """Get external deal ID."""
        return str(self._get_current().get("external_id", ""))

    def select_by_index(self, index: int) -> bool:
        """Select deal by index."""
        if 0 <= index < len(self._deals):
            self._current_index = index
            return True
        return False

    def get_total_deals(self) -> int:
        """Get total number of deals."""
        return len(self._deals)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits from MT5."""
        symbol_info = self._client.get_symbol_info(symbol)
        if symbol_info:
            return int(symbol_info.get("digits", 5))
        return 5


class BacktestDealProvider:
    """
    Implementation of DealDataProvider for backtesting.

    This provider allows programmatic creation and management of deals
    for backtesting scenarios without requiring an MT5 connection.
    """

    def __init__(self):
        """Initialize BacktestDealProvider with empty deal history."""
        self._deals: List[Dict[str, Any]] = []
        self._current_index = -1

    def add_deal(
        self,
        ticket: int,
        order: int,
        time: datetime,
        deal_type: DealType,
        entry: DealEntry,
        symbol: str,
        volume: float,
        price: float,
        commission: float = 0.0,
        swap: float = 0.0,
        profit: float = 0.0,
        fee: float = 0.0,
        comment: str = "",
        magic: int = 0,
        position_id: int = 0,
        external_id: str = "",
    ) -> None:
        """
        Add a deal to the backtest history.

        Args:
            ticket: Deal ticket number
            order: Order ticket that created this deal
            time: Deal execution time
            deal_type: Type of deal (BUY/SELL)
            entry: Entry type (IN/OUT/INOUT/OUT_BY)
            symbol: Trading symbol
            volume: Deal volume in lots
            price: Deal execution price
            commission: Commission charged
            swap: Swap charged
            profit: Deal profit
            fee: Additional fee
            comment: Deal comment
            magic: Magic number
            position_id: Position ID
            external_id: External deal ID
        """
        deal_data = {
            "ticket": ticket,
            "order": order,
            "time": int(time.timestamp()),
            "time_msc": int(time.timestamp() * 1000),
            "type": self._map_deal_type_to_int(deal_type),
            "entry": self._map_deal_entry_to_int(entry),
            "symbol": symbol,
            "volume": volume,
            "price": price,
            "commission": commission,
            "swap": swap,
            "profit": profit,
            "fee": fee,
            "comment": comment,
            "magic": magic,
            "position_id": position_id,
            "external_id": external_id,
        }
        self._deals.append(deal_data)
        if self._current_index == -1 and self._deals:
            self._current_index = 0

    def _map_deal_type_to_int(self, deal_type: DealType) -> int:
        """Map DealType enum to integer code."""
        type_map = {
            DealType.BUY: 0,
            DealType.SELL: 1,
            DealType.BALANCE: 2,
            DealType.CREDIT: 3,
            DealType.CHARGE: 4,
            DealType.CORRECTION: 5,
            DealType.BONUS: 6,
            DealType.COMMISSION: 7,
            DealType.COMMISSION_DAILY: 8,
            DealType.COMMISSION_MONTHLY: 9,
            DealType.COMMISSION_AGENT_DAILY: 10,
            DealType.COMMISSION_AGENT_MONTHLY: 11,
            DealType.INTEREST: 12,
            DealType.BUY_CANCELED: 13,
            DealType.SELL_CANCELED: 14,
        }
        return type_map.get(deal_type, -1)

    def _map_deal_entry_to_int(self, entry: DealEntry) -> int:
        """Map DealEntry enum to integer code."""
        entry_map = {
            DealEntry.IN: 0,
            DealEntry.OUT: 1,
            DealEntry.INOUT: 2,
            DealEntry.OUT_BY: 3,
        }
        return entry_map.get(entry, -1)

    def clear_deals(self) -> None:
        """Clear all deals from history."""
        self._deals = []
        self._current_index = -1

    def _get_current(self) -> Dict[str, Any]:
        """Get current deal data."""
        if 0 <= self._current_index < len(self._deals):
            return self._deals[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get deal ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_order(self) -> int:
        """Get order ticket."""
        return int(self._get_current().get("order", 0))

    def get_time(self) -> datetime:
        """Get deal time."""
        return datetime.fromtimestamp(self._get_current().get("time", 0))

    def get_time_msc(self) -> int:
        """Get deal time in milliseconds."""
        return int(self._get_current().get("time_msc", 0))

    def get_deal_type(self) -> DealType:
        """Get deal type."""
        val = self._get_current().get("type", -1)
        if isinstance(val, DealType):
            return val
        type_map = {0: DealType.BUY, 1: DealType.SELL}
        return type_map.get(val, DealType.UNKNOWN)

    def get_entry(self) -> DealEntry:
        """Get deal entry."""
        val = self._get_current().get("entry", -1)
        if isinstance(val, DealEntry):
            return val
        entry_map = {
            0: DealEntry.IN,
            1: DealEntry.OUT,
            2: DealEntry.INOUT,
            3: DealEntry.OUT_BY,
        }
        return entry_map.get(val, DealEntry.UNKNOWN)

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_position_id(self) -> int:
        """Get position ID."""
        return int(self._get_current().get("position_id", 0))

    def get_volume(self) -> float:
        """Get deal volume."""
        return float(self._get_current().get("volume", 0.0))

    def get_price(self) -> float:
        """Get deal price."""
        return float(self._get_current().get("price", 0.0))

    def get_commission(self) -> float:
        """Get commission."""
        return float(self._get_current().get("commission", 0.0))

    def get_swap(self) -> float:
        """Get swap."""
        return float(self._get_current().get("swap", 0.0))

    def get_profit(self) -> float:
        """Get profit."""
        return float(self._get_current().get("profit", 0.0))

    def get_fee(self) -> float:
        """Get deal fee."""
        return float(self._get_current().get("fee", 0.0))

    def get_symbol(self) -> str:
        """Get symbol name."""
        return str(self._get_current().get("symbol", ""))

    def get_comment(self) -> str:
        """Get deal comment."""
        return str(self._get_current().get("comment", ""))

    def get_external_id(self) -> str:
        """Get external deal ID."""
        return str(self._get_current().get("external_id", ""))

    def select_by_index(self, index: int) -> bool:
        """Select deal by index."""
        if 0 <= index < len(self._deals):
            self._current_index = index
            return True
        return False

    def get_total_deals(self) -> int:
        """Get total number of deals."""
        return len(self._deals)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits (default to 5 for backtest)."""
        return 5


class DealInfo:
    """
    Class for accessing historical deal information.

    This class provides a clean interface to deal information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Deals represent actual trade executions - when an order is filled,
    one or more deals are created. Deals contain commission, swap,
    and profit information.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import DealInfo, MT5DealProvider

        client = MT5Client()
        client.initialize()
        provider = MT5DealProvider(client, date_from=datetime(2024, 1, 1))
        deal = DealInfo(provider)

        # Iterate through history
        for i in range(deal.total_deals()):
            if deal.select_by_index(i):
                print(f"Deal: {deal.format_deal()}")
                print(f"Profit: {deal.profit()}")
    """

    def __init__(self, data_provider: DealDataProvider):
        """
        Initialize DealInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          DealDataProvider protocol.
                          Use MT5DealProvider for live trading.
        """
        self._provider = data_provider
        self._ticket: int = 0

    def total_deals(self) -> int:
        """
        Get total number of deals.

        Returns:
            Total count of deals.
        """
        return self._provider.get_total_deals()

    def ticket(self, ticket: Optional[int] = None) -> int:
        """
        Get or set deal ticket/ID.

        Args:
            ticket: If provided, sets the ticket. If None, returns current ticket.

        Returns:
            Current deal ticket number.
        """
        if ticket is not None:
            self._ticket = ticket
        return self._ticket

    # Fast access methods to integer deal properties

    def order(self) -> int:
        """
        Get order ticket that created this deal.

        Returns:
            Order ticket number.
        """
        return self._provider.get_order()

    def time(self) -> datetime:
        """
        Get deal execution time.

        Returns:
            Deal execution datetime.
        """
        return self._provider.get_time()

    def time_msc(self) -> int:
        """
        Get deal execution time in milliseconds.

        Returns:
            Deal execution time in milliseconds since epoch.
        """
        return self._provider.get_time_msc()

    def deal_type(self) -> DealType:
        """
        Get deal type.

        Returns:
            DealType enum value.
        """
        return self._provider.get_deal_type()

    def type_description(self) -> str:
        """
        Get deal type as a descriptive string.

        Returns:
            Human-readable description of deal type.
        """
        type_map = {
            DealType.BUY: "Buy type",
            DealType.SELL: "Sell type",
            DealType.BALANCE: "Balance type",
            DealType.CREDIT: "Credit type",
            DealType.CHARGE: "Charge type",
            DealType.CORRECTION: "Correction type",
            DealType.BONUS: "Bonus type",
            DealType.COMMISSION: "Commission type",
            DealType.COMMISSION_DAILY: "Daily Commission type",
            DealType.COMMISSION_MONTHLY: "Monthly Commission type",
            DealType.COMMISSION_AGENT_DAILY: "Daily Agent Commission type",
            DealType.COMMISSION_AGENT_MONTHLY: "Monthly Agent Commission type",
            DealType.INTEREST: "Interest Rate type",
            DealType.BUY_CANCELED: "Canceled Buy type",
            DealType.SELL_CANCELED: "Canceled Sell type",
        }
        return type_map.get(self.deal_type(), "Unknown type")

    def entry(self) -> DealEntry:
        """
        Get deal entry direction.

        Returns:
            DealEntry enum value.
        """
        return self._provider.get_entry()

    def entry_description(self) -> str:
        """
        Get deal entry as a descriptive string.

        Returns:
            Human-readable description of entry direction.
        """
        entry_map = {
            DealEntry.IN: "In entry",
            DealEntry.OUT: "Out entry",
            DealEntry.INOUT: "InOut entry",
            DealEntry.STATE: "Status record",
            DealEntry.OUT_BY: "Out By entry",
        }
        return entry_map.get(self.entry(), "Unknown entry")

    def magic(self) -> int:
        """
        Get magic number.

        Returns:
            Magic number used to identify the deal.
        """
        return self._provider.get_magic()

    def position_id(self) -> int:
        """
        Get position ID.

        Returns:
            Position ID that this deal belongs to.
        """
        return self._provider.get_position_id()

    # Fast access methods to double deal properties

    def volume(self) -> float:
        """
        Get deal volume.

        Returns:
            Deal volume in lots.
        """
        return self._provider.get_volume()

    def price(self) -> float:
        """
        Get deal price.

        Returns:
            Execution price.
        """
        return self._provider.get_price()

    def commission(self) -> float:
        """
        Get deal commission.

        Returns:
            Commission charged for this deal.
        """
        return self._provider.get_commission()

    def swap(self) -> float:
        """
        Get deal swap.

        Returns:
            Swap/rollover charged or credited.
        """
        return self._provider.get_swap()

    def profit(self) -> float:
        """
        Get deal profit.

        Returns:
            Profit (positive) or loss (negative) for this deal.
        """
        return self._provider.get_profit()

    # Fast access methods to string deal properties

    def symbol(self) -> str:
        """
        Get deal symbol.

        Returns:
            Trading symbol (e.g., "EURUSD").
        """
        return self._provider.get_symbol()

    def comment(self) -> str:
        """
        Get deal comment.

        Returns:
            Deal comment string.
        """
        return self._provider.get_comment()

    def external_id(self) -> str:
        """
        Get external deal ID.

        Returns:
            External deal ID from exchange.
        """
        return self._provider.get_external_id()

    # Info methods

    @staticmethod
    def format_action(deal_type: DealType) -> str:
        """
        Convert deal type to text.

        Args:
            deal_type: DealType enum value.

        Returns:
            Human-readable deal type string.
        """
        action_map = {
            DealType.BUY: "buy",
            DealType.SELL: "sell",
            DealType.BALANCE: "balance",
            DealType.CREDIT: "credit",
            DealType.CHARGE: "charge",
            DealType.CORRECTION: "correction",
            DealType.BONUS: "bonus",
            DealType.COMMISSION: "commission",
            DealType.COMMISSION_DAILY: "daily commission",
            DealType.COMMISSION_MONTHLY: "monthly commission",
            DealType.COMMISSION_AGENT_DAILY: "daily agent commission",
            DealType.COMMISSION_AGENT_MONTHLY: "monthly agent commission",
            DealType.INTEREST: "interest rate",
            DealType.BUY_CANCELED: "canceled buy",
            DealType.SELL_CANCELED: "canceled sell",
        }
        return action_map.get(deal_type, f"unknown deal type {deal_type.value}")

    @staticmethod
    def format_entry(entry: DealEntry) -> str:
        """
        Convert deal entry to text.

        Args:
            entry: DealEntry enum value.

        Returns:
            Human-readable entry direction string.
        """
        entry_map = {
            DealEntry.IN: "in",
            DealEntry.OUT: "out",
            DealEntry.INOUT: "in/out",
            DealEntry.OUT_BY: "out by",
            DealEntry.STATE: "state",
        }
        return entry_map.get(entry, f"unknown deal entry {entry.value}")

    def format_deal(self) -> str:
        """
        Format deal parameters as text.

        Returns:
            Formatted string describing the deal.
        """
        deal_type = self.deal_type()

        # Trade deals (buy/sell)
        if deal_type in [
            DealType.BUY,
            DealType.SELL,
            DealType.BUY_CANCELED,
            DealType.SELL_CANCELED,
        ]:
            symbol_name = self.symbol()
            digits = self._provider.get_symbol_digits(symbol_name)
            type_str = self.format_action(deal_type)

            return (
                f"#{self._ticket} {type_str} "
                f"{self.volume():.2f} {symbol_name} "
                f"at {self.price():.{digits}f}"
            )

        # Balance operations
        elif deal_type in [
            DealType.BALANCE,
            DealType.CREDIT,
            DealType.CHARGE,
            DealType.CORRECTION,
            DealType.BONUS,
            DealType.COMMISSION,
            DealType.COMMISSION_DAILY,
            DealType.COMMISSION_MONTHLY,
            DealType.COMMISSION_AGENT_DAILY,
            DealType.COMMISSION_AGENT_MONTHLY,
            DealType.INTEREST,
        ]:
            type_str = self.format_action(deal_type)
            comment = self.comment()

            return f"#{self._ticket} {type_str} " f"{self.profit():.2f} [{comment}]"

        else:
            return f"unknown deal type {deal_type.value}"

    # Methods for selecting deals

    def select_by_index(self, index: int) -> bool:
        """
        Select deal by index in the history.

        Args:
            index: Deal index (0-based).

        Returns:
            True if deal exists at index and was selected, False otherwise.
        """
        if self._provider.select_by_index(index):
            self._ticket = self._provider.get_ticket()
            return True

        self._ticket = 0
        return False

    def __repr__(self) -> str:
        """Return string representation of DealInfo."""
        try:
            return (
                f"DealInfo(ticket={self._ticket}, "
                f"symbol={self.symbol()}, "
                f"type={self.deal_type().value}, "
                f"entry={self.entry().value}, "
                f"volume={self.volume():.2f}, "
                f"profit={self.profit():.2f})"
            )
        except Exception:
            return "DealInfo(no deal selected)"
