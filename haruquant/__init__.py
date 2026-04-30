"""HaruQuant: High-performance algorithmic trading and backtesting library."""

from .data import (
    Data,
    DataCache,
    MT5Data,
    DukascopyData,
    YFData,
    BinanceData,
    CCXTData,
    CSVData,
    ParquetData,
    GBMData,
    ScheduledDataUpdater,
    DataSplitter,
    Labeler,
    DataSaver,
    CSVDataSaver,
    ParquetDataSaver
)

from . import indicators as ind
from . import common
from .common import resample, merge, concat, symbol_dict

# Convenience exports
from .indicators import ema, sma, rsi, bbands, atr, hurst, fvg, ob, bos_choch, phl, ta, list_indicators, indicator, run_indicators

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
    "CSVData",
    "ParquetData",
    "GBMData",
    "ScheduledDataUpdater",
    "DataSplitter",
    "Labeler",
    "DataSaver",
    "CSVDataSaver",
    "ParquetDataSaver",
    "ind",
    "common",
    "resample",
    "merge",
    "concat",
    "symbol_dict",
    "ema",
    "sma",
    "rsi",
    "bbands",
    "atr",
    "hurst",
    "fvg",
    "ob",
    "bos_choch",
    "phl",
    "ta",
    "list_indicators",
    "indicator",
    "run_indicators",
    "Catalog",
    "Portfolio",
    "StrategyCatalogCreateRequest",
    "StrategyCatalogUpdateRequest",
    "TrendFollowingStrategy",
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "CloseBreakoutStrategy"
]
