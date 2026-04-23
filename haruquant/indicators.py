import pandas as pd
from typing import Union, List, Optional, Any, Callable
from haruquant.data import Data

class Indicator:
    """Base class for indicator wrappers."""
    
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func

    def run(self, data: Union[pd.DataFrame, Data], period: Union[int, List[int]], **kwargs) -> pd.DataFrame:
        """
        Run the indicator on the data.
        
        Args:
            data: The input data (DataFrame or Data object).
            period: A single integer or a list of integers for multiple periods.
            **kwargs: Additional arguments for the underlying indicator function.
            
        Returns:
            DataFrame with the indicator columns added.
        """
        if isinstance(data, Data):
            df = data.df
        else:
            df = data
            
        periods = [period] if isinstance(period, int) else period
        
        result_df = df.copy()
        for p in periods:
            # We call the underlying func. 
            # Local logic: data = func(data, p, **kwargs)
            # Most of our local indicators take 'span', 'window', or 'period'
            # We need to map the argument name based on the function signature or common patterns.
            
            # Identify the correct parameter name (window for SMA, span for EMA, etc.)
            arg_name = kwargs.pop("arg_name", None)
            if not arg_name:
                if self.name in ["ema"]:
                    arg_name = "span"
                elif self.name in ["sma", "wma"]:
                    arg_name = "window"
                elif self.name in ["rsi", "atr", "bbands"]:
                    arg_name = "period"
                else:
                    arg_name = "period" # fallback
            
            call_kwargs = {arg_name: p, **kwargs}
            # The local functions return a NEW dataframe with the column added
            # So we pass result_df to each call to accumulate columns
            result_df = self.func(result_df, **call_kwargs)
            
        return result_df

# Import local implementations
from backend.services.indicators.trend.ema import ema as _ema
from backend.services.indicators.trend.sma import sma as _sma
from backend.services.indicators.trend.wma import wma as _wma
from backend.services.indicators.momentum.rsi import rsi as _rsi
from backend.services.indicators.volatility.atr import atr as _atr
from backend.services.indicators.volatility.bbands import bbands as _bbands

# Expose indicators
ema = Indicator("ema", _ema)
sma = Indicator("sma", _sma)
wma = Indicator("wma", _wma)
rsi = Indicator("rsi", _rsi)
atr = Indicator("atr", _atr)
bbands = Indicator("bbands", _bbands)

# Support for Pandas TA integration
class PandasTAIndicator:
    """Wrapper for Pandas TA indicators."""
    def __getattr__(self, name):
        def _run(data: Union[pd.DataFrame, Data], period: Union[int, List[int]], **kwargs):
            try:
                import pandas_ta as ta
            except ImportError:
                raise ImportError("pandas_ta is required. Install with 'pip install pandas-ta'")
                
            if isinstance(data, Data):
                df = data.df
            else:
                df = data
                
            periods = [period] if isinstance(period, int) else period
            result_df = df.copy()
            
            # Map standard names to pandas_ta methods if they differ
            ta_method = getattr(result_df.ta, name)
            
            for p in periods:
                # pandas_ta usually adds columns in-place or returns a series
                # We want to match our local naming convention: {name}_{p}
                indicator_series = ta_method(length=p, **kwargs)
                if isinstance(indicator_series, pd.Series):
                    result_df[f"{name}_{p}"] = indicator_series
                elif isinstance(indicator_series, pd.DataFrame):
                    # For multi-column indicators (like MACD), we might need special handling
                    # but for simple ones we just join
                    for col in indicator_series.columns:
                        result_df[f"{col}_{p}"] = indicator_series[col]
                        
            return result_df
        return _run

ta = PandasTAIndicator()
