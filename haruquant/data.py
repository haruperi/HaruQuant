import pandas as pd
from typing import Optional, Union, List, Any
from datetime import datetime
import os
import sys

# Ensure backend is in sys.path if not already
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

class Data:
    """Wrapper class for trading data, mimicking VectorBT's Data object."""
    
    def __init__(self, df: pd.DataFrame, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        self._df = df
        self._symbol = symbol
        self._timeframe = timeframe

    def get(self, column: str = "close") -> pd.Series:
        """Get a specific column from the data."""
        col = column.lower()
        if col in self._df.columns:
            return self._df[col]
        # Try to find a match if exact lowercase fails
        for c in self._df.columns:
            if c.lower() == col:
                return self._df[c]
        raise ValueError(f"Column '{column}' not found in data. Available: {list(self._df.columns)}")

    @property
    def close(self) -> pd.Series:
        return self.get("close")

    @property
    def open(self) -> pd.Series:
        return self.get("open")

    @property
    def high(self) -> pd.Series:
        return self.get("high")

    @property
    def low(self) -> pd.Series:
        return self.get("low")

    @property
    def volume(self) -> pd.Series:
        return self.get("volume")

    @property
    def df(self) -> pd.DataFrame:
        """Returns the underlying DataFrame."""
        return self._df

    def __repr__(self):
        return f"<HaruQuant Data: {self._symbol} {self._timeframe} ({len(self._df)} rows)>"


class MT5Data:
    """Data source for MetaTrader 5."""
    
    @staticmethod
    def download(
        symbol: str,
        timeframe: str = "H1",
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        count: Optional[int] = None,
        **kwargs
    ) -> Data:
        """Download data from MT5."""
        from backend.services.market_data.data_getters import load_mt5
        
        df = load_mt5(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
            count=count or 0,
            **kwargs
        )
        if df is None:
            raise ValueError(f"Failed to download MT5 data for {symbol}")
            
        return Data(df, symbol=symbol, timeframe=timeframe)


class DukascopyData:
    """Data source for Dukascopy."""
    
    @staticmethod
    def download(
        symbol: str,
        timeframe: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        count: Optional[int] = None,
        **kwargs
    ) -> Data:
        """Download data from Dukascopy API."""
        from backend.services.market_data.data_getters import load_dukascopy
        
        df = load_dukascopy(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start,
            end_date=end,
            count=count,
            **kwargs
        )
        if df is None or df.empty:
            raise ValueError(f"Failed to download Dukascopy data for {symbol}")
            
        return Data(df, symbol=symbol, timeframe=timeframe)


class YFData:
    """Data source for Yahoo Finance."""
    
    @staticmethod
    def download(
        symbol: Union[str, List[str]],
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        period: Optional[str] = None,
        interval: str = "1d",
        **kwargs
    ) -> Data:
        """Download data from Yahoo Finance."""
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance is required for YFData. Install with 'pip install yfinance'")
            
        df = yf.download(
            tickers=symbol,
            start=start,
            end=end,
            period=period,
            interval=interval,
            **kwargs
        )
        
        if df.empty:
            raise ValueError(f"Failed to download Yahoo Finance data for {symbol}")
            
        # Normalize column names to lowercase for consistency
        if isinstance(df.columns, pd.MultiIndex):
            # For MultiIndex, we lower the top level (Price) and keep the rest
            df.columns = df.columns.set_levels([l.lower() for l in df.columns.levels[0]], level=0)
        else:
            df.columns = [str(c).lower() for c in df.columns]
        
        return Data(df, symbol=str(symbol), timeframe=interval)


class BinanceData:
    """Data source for Binance."""
    
    @staticmethod
    def download(
        symbol: str,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        interval: str = "1d",
        **kwargs
    ) -> Data:
        """Download data from Binance."""
        try:
            from binance import Client
        except ImportError:
            raise ImportError("python-binance is required for BinanceData. Install with 'pip install python-binance'")
            
        client = Client(None, None) # Public data doesn't need API keys
        
        # Binance uses specific interval strings (1m, 1h, 1d, etc.)
        # Mapping common interval formats if necessary
        binance_interval = interval
        
        # Convert start/end to strings if they are datetime
        if isinstance(start, datetime):
            start = start.strftime("%d %b %Y %H:%M:%S")
        if isinstance(end, datetime):
            end = end.strftime("%d %b %Y %H:%M:%S")
            
        klines = client.get_historical_klines(symbol, binance_interval, start, end)
        
        cols = [
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ]
        df = pd.DataFrame(klines, columns=cols)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        
        # Convert to numeric
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
            
        return Data(df, symbol=symbol, timeframe=interval)


class CCXTData:
    """Data source for CCXT (supports many exchanges)."""
    
    @staticmethod
    def download(
        symbol: str,
        exchange: str = "binance",
        start: Optional[Union[str, datetime]] = None,
        timeframe: str = "1d",
        limit: int = 1000,
        **kwargs
    ) -> Data:
        """Download data using CCXT."""
        try:
            import ccxt
        except ImportError:
            raise ImportError("ccxt is required for CCXTData. Install with 'pip install ccxt'")
            
        exchange_class = getattr(ccxt, exchange)
        ex = exchange_class()
        
        since = None
        if start:
            if isinstance(start, str):
                since = ex.parse8601(start)
            elif isinstance(start, datetime):
                since = int(start.timestamp() * 1000)
                
        ohlcv = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        
        cols = ["timestamp", "open", "high", "low", "close", "volume"]
        df = pd.DataFrame(ohlcv, columns=cols)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        
        return Data(df, symbol=symbol, timeframe=timeframe)


class GBMData:
    """Geometric Brownian Motion (GBM) Data Generator."""
    
    @staticmethod
    def generate(
        symbols: Union[str, List[str]],
        start: Union[str, datetime] = "2020-01-01",
        end: Union[str, datetime] = "2021-01-01",
        interval: str = "1d",
        mu: float = 0.0,
        sigma: float = 0.01,
        start_value: float = 100.0,
        seed: Optional[int] = None,
        **kwargs
    ) -> Data:
        """Generate synthetic price data using GBM."""
        import numpy as np
        
        if isinstance(symbols, str):
            symbols = [symbols]
            
        date_range = pd.date_range(start=start, end=end, freq=interval)
        n_steps = len(date_range)
        
        if seed is not None:
            np.random.seed(seed)
            
        data_dict = {}
        for sym in symbols:
            # GBM formula: S(t) = S(0) * exp((mu - 0.5 * sigma^2) * t + sigma * W(t))
            # Simpler version for increments: r = (mu - 0.5 * sigma^2) * dt + sigma * epsilon * sqrt(dt)
            returns = np.random.normal(mu, sigma, n_steps)
            price = start_value * np.exp(np.cumsum(returns))
            data_dict[sym] = price
            
        df = pd.DataFrame(data_dict, index=date_range)
        # Mock OHLC from close
        if len(symbols) == 1:
            df["close"] = df[symbols[0]]
            df["open"] = df["close"].shift(1).fillna(start_value)
            df["high"] = df[["open", "close"]].max(axis=1) * (1 + abs(np.random.normal(0, 0.001, n_steps)))
            df["low"] = df[["open", "close"]].min(axis=1) * (1 - abs(np.random.normal(0, 0.001, n_steps)))
            df["volume"] = np.random.uniform(100, 1000, n_steps)
            # Reorder columns
            df = df[["open", "high", "low", "close", "volume"]]
        
        return Data(df, symbol=str(symbols), timeframe=interval)


class ScheduledDataUpdater:
    """Scheduled Data Updates utility."""
    
    def __init__(self, data: Data, update_func: callable, interval_sec: int = 60):
        self.data = data
        self._df = data.df
        self.update_func = update_func
        self.interval_sec = interval_sec
        self._running = False
        
    def update(self):
        """Perform a single update."""
        prev_len = len(self._df)
        new_data = self.update_func(self.data)
        
        if new_data is not None and not new_data.df.empty:
            # Merge and filter duplicates
            combined = pd.concat([self._df, new_data.df])
            self._df = combined[~combined.index.duplicated(keep='last')].sort_index()
            # Update the original Data object's internal DF if possible or just store locally
            self.data._df = self._df 
            
        print(f"Data updated. Added {len(self._df) - prev_len} new points. Total: {len(self._df)}")
        return len(self._df) - prev_len

    def start(self):
        """Start periodic updates (blocking)."""
        import time
        self._running = True
        print(f"Starting scheduled updates every {self.interval_sec} seconds...")
        try:
            while self._running:
                self.update()
                time.sleep(self.interval_sec)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop periodic updates."""
        self._running = False
        print("Scheduled updates stopped.")


class DataSplitter:
    """Utilities for data splitting and preparation."""
    
    @staticmethod
    def rolling_split(
        data: Union[pd.Series, pd.DataFrame, Data],
        window_len: int,
        set_lens: tuple = (1, 1),
        left_to_right: bool = False,
    ) -> List[dict]:
        """
        Perform a rolling split of the data into training and testing sets.
        Mimics vbt.rolling_split.
        
        Args:
            data: The data to split.
            window_len: Total length of the window (train + test).
            set_lens: Relative lengths of (train, test) or (train, valid, test).
            left_to_right: Direction of the rolling window.
            
        Returns:
            A list of dictionaries containing 'train', 'valid' (optional), and 'test' subsets.
        """
        if isinstance(data, Data):
            df = data.df
        else:
            df = data
            
        n = len(df)
        splits = []
        
        total_set_len = sum(set_lens)
        # Normalize set_lens to be fractions of window_len
        unit = window_len / total_set_len
        actual_lens = [int(l * unit) for l in set_lens]
        
        if left_to_right:
            indices = range(0, n - window_len + 1)
        else:
            indices = range(n - window_len, -1, -1)
            
        for i in indices:
            current_window = df.iloc[i : i + window_len]
            split = {}
            start = 0
            
            names = ['train', 'valid', 'test'] if len(set_lens) == 3 else ['train', 'test']
            for name, length in zip(names, actual_lens):
                split[name] = current_window.iloc[start : start + length]
                start += length
                
            splits.append(split)
            
        return splits if left_to_right else splits[::-1]


class Labeler:
    """Utilities for machine learning labeling."""
    
    @staticmethod
    def lexlb(
        data: Union[pd.Series, Data],
        up_threshold: float,
        down_threshold: float
    ) -> pd.Series:
        """
        Local Extrema Labeling (LEXLB).
        Identifies local peaks and troughs based on percentage change thresholds.
        
        Returns a Series where 1 is a peak, -1 is a trough, and 0 is neutral.
        """
        if isinstance(data, Data):
            series = data.close
        else:
            series = data
            
        labels = pd.Series(0, index=series.index)
        if len(series) < 2:
            return labels
            
        last_extrema_val = series.iloc[0]
        last_extrema_idx = series.index[0]
        mode = 0 # 1 for searching peak, -1 for searching trough, 0 for initial
        
        for i in range(1, len(series)):
            curr_val = series.iloc[i]
            
            # Simple zigzag-like logic
            if mode == 0:
                if curr_val >= last_extrema_val * (1 + up_threshold):
                    mode = 1
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
                elif curr_val <= last_extrema_val * (1 - down_threshold):
                    mode = -1
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
            elif mode == 1: # Searching for new peak, or reversal to trough
                if curr_val > last_extrema_val:
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
                elif curr_val <= last_extrema_val * (1 - down_threshold):
                    labels.loc[last_extrema_idx] = 1 # Mark the peak
                    mode = -1
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
            elif mode == -1: # Searching for new trough, or reversal to peak
                if curr_val < last_extrema_val:
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
                elif curr_val >= last_extrema_val * (1 + up_threshold):
                    labels.loc[last_extrema_idx] = -1 # Mark the trough
                    mode = 1
                    last_extrema_val = curr_val
                    last_extrema_idx = series.index[i]
                    
        return labels
