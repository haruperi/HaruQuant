"""HaruQuant: High-performance algorithmic trading and backtesting library."""

from .data import (
    Data, 
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
# Convenience exports
from .indicators import ema, sma, rsi, bbands, atr, ta

__all__ = [
    "Data", 
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
    "ema",
    "sma",
    "rsi",
    "bbands",
    "atr",
    "ta"
]
