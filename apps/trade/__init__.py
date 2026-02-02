"""Live and Simulation trade classes aligned with the MQL5 Standard Library."""

from .account_info import AccountInfo
from .deal_info import DealInfo
from .history_order_info import HistoryOrderInfo
from .order_info import OrderInfo
from .position_info import PositionInfo
from .symbol_info import SymbolInfo
from .terminal_info import TerminalInfo
from .trade import Trade

__all__ = [
    "AccountInfo",
    "SymbolInfo",
    "DealInfo",
    "HistoryOrderInfo",
    "OrderInfo",
    "PositionInfo",
    "TerminalInfo",
    "Trade",
    "TradeSimulator",
]


def __getattr__(name: str):
    if name == "TradeSimulator":
        from apps.simulation.simulator import TradeSimulator

        return TradeSimulator
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
