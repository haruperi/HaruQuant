"""MT5-specific trade classes aligned with the MQL5 Standard Library."""

from .caccountinfo import CAccountInfo
from .cdealinfo import CDealInfo
from .chistoryorderinfo import CHistoryOrderInfo
from .corderinfo import COrderInfo
from .cpositioninfo import CPositionInfo
from .csymbolinfo import CSymbolInfo
from .cterminalinfo import CTerminalInfo
from .ctrade import CTrade

__all__ = [
    "CAccountInfo",
    "CDealInfo",
    "CHistoryOrderInfo",
    "COrderInfo",
    "CPositionInfo",
    "CTrade",
    "CTerminalInfo",
    "CSymbolInfo",
]
