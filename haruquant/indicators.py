import pandas as pd
from typing import Union, List, Optional, Any, Callable
from haruquant.data import Data

class Indicator:
    """Base class for indicator wrappers."""
    
    _registry = {}
    
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func
        Indicator._registry[name] = self

    def _run_single(self, df: pd.DataFrame, p: Any, **kwargs) -> pd.DataFrame:
        """Run a single period and return the resulting DataFrame."""
        # Identify the correct parameter name (window for SMA, span for EMA, etc.)
        arg_name = kwargs.pop("arg_name", None)
        if not arg_name:
            if self.name in ["ema"]: arg_name = "span"
            elif self.name in ["sma", "wma"]: arg_name = "window"
            elif self.name in ["rsi", "atr", "bbands"]: arg_name = "period"
            elif self.name in ["ob", "bos_choch", "swing_highs_lows"]: arg_name = "swing_length"
            elif self.name in ["phl"]: arg_name = "timeframe"
            else: arg_name = None
        
        call_kwargs = kwargs.copy()
        if arg_name is not None:
            call_kwargs[arg_name] = p
            
        return self.func(df, **call_kwargs)

    def run(self, data: Union[pd.DataFrame, Data], period: Union[int, List[int], str, None] = None, **kwargs) -> pd.DataFrame:
        """
        Run the indicator on the data.
        
        Args:
            data: The input data (DataFrame or Data object).
            period: A single integer or a list of integers for multiple periods.
            engine: Execution engine ("serial", "threadpool", "processpool"). Default is "serial".
            n_workers: Number of workers for parallel execution.
            **kwargs: Additional arguments for the underlying indicator function.
            
        Returns:
            DataFrame with the indicator columns added.
        """
        if isinstance(data, Data):
            df = data.df
        else:
            df = data
            
        if period is None:
            periods = [None]
        else:
            periods = [period] if isinstance(period, (int, str)) else period
            
        engine = kwargs.pop("engine", "serial")
        n_workers = kwargs.pop("n_workers", None)
        
        if engine == "serial" or len(periods) <= 1:
            result_df = df.copy()
            for p in periods:
                result_df = self._run_single(result_df, p, **kwargs)
            return result_df
        
        # Parallel execution
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
        
        Executor = ThreadPoolExecutor if engine == "threadpool" else ProcessPoolExecutor
        
        results = []
        with Executor(max_workers=n_workers) as executor:
            # We submit each period independently on the original DF
            futures = [executor.submit(self._run_single, df, p, **kwargs) for p in periods]
            results = [f.result() for f in futures]
            
        # Merge results: combine new columns from each parallel run
        final_df = df.copy()
        orig_cols = set(df.columns)
        for res in results:
            new_cols = [c for c in res.columns if c not in orig_cols]
            for c in new_cols:
                final_df[c] = res[c]
                
        return final_df

# Import local implementations
from backend.services.indicators.trend.ema import ema as _ema
from backend.services.indicators.trend.sma import sma as _sma
from backend.services.indicators.trend.wma import wma as _wma
from backend.services.indicators.momentum.rsi import rsi as _rsi
from backend.services.indicators.volatility.atr import atr as _atr
from backend.services.indicators.volatility.bbands import bbands as _bbands
from backend.services.indicators.statistical.hurst import hurst as _hurst
from backend.services.indicators.custom.smc import fvg as _fvg, ob as _ob, bos_choch as _bos_choch, previous_high_low as _phl

# Expose indicators
ema = Indicator("ema", _ema)
sma = Indicator("sma", _sma)
wma = Indicator("wma", _wma)
rsi = Indicator("rsi", _rsi)
atr = Indicator("atr", _atr)
bbands = Indicator("bbands", _bbands)
hurst = Indicator("hurst", _hurst)
fvg = Indicator("fvg", _fvg)
ob = Indicator("ob", _ob)
bos_choch = Indicator("bos_choch", _bos_choch)
phl = Indicator("phl", _phl)

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

def list_indicators(pattern: str = "*") -> List[str]:
    """List all available indicators matching a pattern."""
    import fnmatch
    names = list(Indicator._registry.keys())
    
    # Also include pandas_ta indicators if pattern matches
    try:
        import pandas_ta as pta
        # We only add them if specifically asked or if pattern is broad
        if "*" in pattern or "ta:" in pattern:
            # Get list of ta methods
            ta_names = [f"ta:{m}" for m in dir(pta.DataFrame) if not m.startswith("_") and callable(getattr(pta.DataFrame, m))]
            names.extend(ta_names)
    except ImportError:
        pass
        
    return fnmatch.filter(names, pattern)

def indicator(name: str) -> Any:
    """Get an indicator by name."""
    if name.startswith("ta:"):
        indicator_name = name.split(":", 1)[1]
        return getattr(ta, indicator_name)
    
    if name in Indicator._registry:
        return Indicator._registry[name]
        
    raise ValueError(f"Indicator '{name}' not found.")

def run_indicators(data: Any, package: str, **kwargs) -> pd.DataFrame:
    """
    Run multiple indicators on the data simultaneously.
    
    Args:
        data: Input Data or DataFrame.
        package: Package name ("native", "ta", "smc") or a search pattern.
        **kwargs: Arguments to be passed to all indicators (e.g., period=14).
        
    Returns:
        DataFrame with all calculated features.
    """
    if package == "native":
        # All indicators NOT prefixed with ta:
        inds = [i for i in list_indicators("*") if not i.startswith("ta:")]
    elif package == "ta":
        # All pandas_ta indicators
        inds = list_indicators("ta:*")
    elif package == "smc":
        # Specifically SMC related
        inds = ["fvg", "ob", "bos_choch", "phl"]
    else:
        # Use as a pattern
        inds = list_indicators(package)
        
    if not inds:
        print(f"No indicators found for package/pattern: {package}")
        return data.df if hasattr(data, 'df') else data.copy()
        
    res_df = data.df.copy() if hasattr(data, 'df') else data.copy()
    period = kwargs.pop("period", None)
    
    for name in inds:
        try:
            ind_obj = indicator(name)
            # Some indicators might fail due to data requirements or params
            res_df = ind_obj.run(res_df, period=period, **kwargs)
        except Exception:
            pass
            
    return res_df
