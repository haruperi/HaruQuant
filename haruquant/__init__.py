"""HaruQuant: High-performance algorithmic trading and backtesting library."""

from .data import (
    Data,
    DataCache,
    MT5Data,
    DukascopyData,
    YFData,
    BinanceData,
    CCXTData,
    GBMData,
    ScheduledDataUpdater,
    DataSplitter,
    Labeler
)

from . import indicators as ind
from . import common
from .common import resample, merge, concat

# Convenience exports
from .indicators import ema, sma, rsi, bbands, atr, ta

from .strategy import (
    Catalog,
    Portfolio,
    StrategyCatalogCreateRequest,
    StrategyCatalogUpdateRequest,
    TrendFollowingStrategy,
    BreakoutStrategy,
    MeanReversionStrategy,
    CloseBreakoutStrategy
)

__all__ = [
    "Data",
    "DataCache",
    "MT5Data",
    "DukascopyData",
    "YFData",
    "BinanceData",
    "CCXTData",
    "GBMData",
    "ScheduledDataUpdater",
    "DataSplitter",
    "Labeler",
    "ind",
    "common",
    "resample",
    "merge",
    "concat",
    "ema",
    "sma",
    "rsi",
    "bbands",
    "atr",
    "ta",
    "Catalog",
    "Portfolio",
    "StrategyCatalogCreateRequest",
    "StrategyCatalogUpdateRequest",
    "TrendFollowingStrategy",
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "CloseBreakoutStrategy"
]
