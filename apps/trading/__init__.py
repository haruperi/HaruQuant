"""
Trade module for account and trading operations.

This module provides platform-agnostic trading functionality
inspired by MT5's trading infrastructure.
"""

from .account_info import (
    AccountDataProvider,
    AccountInfo,
    AccountMarginMode,
    AccountStopoutMode,
    AccountTradeMode,
    BacktestAccountProvider,
    MT5AccountProvider,
)
from .deal_info import (
    BacktestDealProvider,
    DealDataProvider,
    DealEntry,
    DealInfo,
    DealType,
    MT5DealProvider,
)
from .history_order_info import (
    BacktestHistoryOrderProvider,
    HistoryOrderDataProvider,
    HistoryOrderInfo,
    MT5HistoryOrderProvider,
)
from .order_info import (
    BacktestOrderProvider,
    MT5OrderProvider,
    OrderDataProvider,
    OrderInfo,
    OrderState,
    OrderType,
    OrderTypeFilling,
    OrderTypeTime,
)
from .position_info import (
    BacktestPositionProvider,
    MT5PositionProvider,
    PositionDataProvider,
    PositionInfo,
    PositionType,
)
from .symbol_info import (
    BacktestSymbolProvider,
    MT5SymbolProvider,
    SymbolDataProvider,
    SymbolInfo,
)
from .terminal_info import MT5TerminalProvider, TerminalDataProvider, TerminalInfo
from .trade import (
    BacktestTradeProvider,
    LogLevel,
    MT5TradeProvider,
    Trade,
    TradeAction,
    TradeCheckResult,
    TradeRequest,
    TradeResult,
    TradeRetcode,
)

__all__ = [
    "AccountInfo",
    "AccountDataProvider",
    "MT5AccountProvider",
    "BacktestAccountProvider",
    "AccountTradeMode",
    "AccountStopoutMode",
    "AccountMarginMode",
    "OrderType",
    "PositionInfo",
    "PositionDataProvider",
    "MT5PositionProvider",
    "BacktestPositionProvider",
    "PositionType",
    "DealInfo",
    "DealDataProvider",
    "MT5DealProvider",
    "BacktestDealProvider",
    "DealType",
    "DealEntry",
    "OrderInfo",
    "OrderDataProvider",
    "MT5OrderProvider",
    "BacktestOrderProvider",
    "OrderType",
    "OrderState",
    "OrderTypeFilling",
    "OrderTypeTime",
    "HistoryOrderInfo",
    "HistoryOrderDataProvider",
    "MT5HistoryOrderProvider",
    "BacktestHistoryOrderProvider",
    "TerminalInfo",
    "TerminalDataProvider",
    "MT5TerminalProvider",
    "SymbolInfo",
    "SymbolDataProvider",
    "MT5SymbolProvider",
    "BacktestSymbolProvider",
    "Trade",
    "TradeAction",
    "TradeRequest",
    "TradeResult",
    "TradeRetcode",
    "TradeCheckResult",
    "LogLevel",
    "MT5TradeProvider",
    "BacktestTradeProvider",
]
