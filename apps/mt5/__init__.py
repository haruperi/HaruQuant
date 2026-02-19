"""
MT5 - MetaTrader 5 Python Trading System.

A comprehensive Python library for interacting with MetaTrader 5 terminal.

Example:
    >>> from apps.mt5 import MT5Client, MT5Account
    >>> client = MT5Client(login=12345, password='pass', server='server')
    >>> client.connect()
    >>> account = MT5Account(client)
    >>> balance = account.get('balance')
    >>> client.shutdown()
"""

from .__version__ import (
    __author__,
    __author_email__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
    __version_info__,
)

# Core imports
from .client import MT5Api, MT5Client, get_mt5_api
from .trade import Trade
from .util import MT5Utils, TicksGen, timeframe_seconds, AccountInfoSimulator, SymbolInfoSimulator

__all__ = [
    # Version info
    "__version__",
    "__version_info__",
    "__title__",
    "__description__",
    "__url__",
    "__author__",
    "__author_email__",
    "__license__",
    "__copyright__",
    # Core classes
    "MT5Client",
    "MT5Api",
    "get_mt5_api",
    "Trade",
    "MT5Utils",
    "TicksGen",
    "timeframe_seconds",
    "AccountInfoSimulator",
    "SymbolInfoSimulator",
]
