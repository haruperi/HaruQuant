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
    Labeler,
    DataSaver,
    CSVDataSaver,
    ParquetDataSaver
)

from . import indicators as ind
from . import common
from .common import resample, merge, concat, symbol_dict, Param, combine_params

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
from .optimization import Optimizer, Splitter, PortfolioOptimizer
from .performance import rolling_mean, chunked
PFO = PortfolioOptimizer
grid_search = Optimizer.grid_search
random_search = Optimizer.random_search
bayesian = Optimizer.bayesian
genetic = Optimizer.genetic
walk_forward = Optimizer.walk_forward
monte_carlo = Optimizer.monte_carlo

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
    "Labeler",
    "DataSaver",
    "CSVDataSaver",
    "ParquetDataSaver",
    "Splitter",
    "ind",
    "common",
    "resample",
    "merge",
    "concat",
    "symbol_dict",
    "Param",
    "combine_params",
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
    "CloseBreakoutStrategy",
    "Optimizer",
    "PortfolioOptimizer",
    "PFO",
    "rolling_mean",
    "chunked",
    "grid_search",
    "random_search",
    "bayesian",
    "genetic",
    "walk_forward",
    "monte_carlo"
]
