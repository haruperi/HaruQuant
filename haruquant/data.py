import fnmatch
import hashlib
import json
import os
import pickle
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

# Ensure backend is in sys.path if not already
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _normalize_cache_value(value: Any) -> Any:
    """Convert fetch parameters into stable JSON-serializable cache input."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_normalize_cache_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize_cache_value(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, set):
        return sorted(_normalize_cache_value(item) for item in value)
    return value


def _map_timeframe(tf: str) -> str:
    """Map MT5-style timeframe strings to Pandas frequency strings."""
    tf_upper = tf.upper()
    if tf_upper.startswith("H") and tf_upper[1:].isdigit():
        return f"{tf_upper[1:]}h"
    elif tf_upper.startswith("M") and tf_upper[1:].isdigit():
        return f"{tf_upper[1:]}min"
    elif tf_upper.startswith("D") and (len(tf_upper) == 1 or tf_upper[1:].isdigit()):
        num = tf_upper[1:] or "1"
        return f"{num}D"
    elif tf_upper == "W1":
        return "1W"
    elif tf_upper == "MN1":
        return "1MS"
    return tf.lower()


class DataCache:
    """LMDB-backed disk cache for remote data downloads."""

    _default_path = (
        Path(PROJECT_ROOT) / "backend" / "data" / "cache" / "haruquant_data.lmdb"
    )

    @classmethod
    def _get_cache_path(cls) -> Path:
        raw_path = os.getenv("HQT_DATA_CACHE_PATH")
        return Path(raw_path) if raw_path else cls._default_path

    @classmethod
    def _open_env(cls):
        try:
            import lmdb
        except ImportError as exc:
            raise ImportError(
                "lmdb is required for data caching. Install with 'pip install lmdb'"
            ) from exc

        cache_path = cls._get_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.mkdir(parents=True, exist_ok=True)
        return lmdb.open(
            str(cache_path),
            map_size=512 * 1024 * 1024,
            subdir=True,
            create=True,
            lock=True,
            readahead=False,
            writemap=False,
        )

    @classmethod
    def make_key(cls, source_name: str, payload: Dict[str, Any]) -> bytes:
        normalized = _normalize_cache_value(payload)
        encoded = json.dumps(
            {"source": source_name, "params": normalized},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"{source_name}:{digest}".encode("utf-8")

    @classmethod
    def get(cls, source_name: str, payload: Dict[str, Any]) -> Optional[pd.DataFrame]:
        key = cls.make_key(source_name, payload)
        with cls._open_env() as env:
            with env.begin(write=False) as txn:
                raw = txn.get(key)
        if raw is None:
            return None
        return pickle.loads(raw)

    @classmethod
    def set(cls, source_name: str, payload: Dict[str, Any], df: pd.DataFrame) -> None:
        key = cls.make_key(source_name, payload)
        raw = pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL)
        with cls._open_env() as env:
            with env.begin(write=True) as txn:
                txn.put(key, raw)

    @classmethod
    def clear(cls) -> None:
        with cls._open_env() as env:
            default_db = env.open_db()
            with env.begin(write=True) as txn:
                txn.drop(db=default_db, delete=False)


def _build_cache_payload(
    symbol: Union[str, List[str]],
    timeframe: Optional[str],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    payload = dict(params)
    payload["symbol"] = symbol
    payload["timeframe"] = timeframe
    return payload


def _download_with_cache(
    source_name: str,
    symbol: Union[str, List[str]],
    timeframe: Optional[str],
    cache: bool,
    params: Dict[str, Any],
    fetcher: Callable[[], pd.DataFrame],
) -> "Data":
    cache_payload = _build_cache_payload(symbol=symbol, timeframe=timeframe, params=params)

    if cache:
        cached_df = DataCache.get(source_name, cache_payload)
        if cached_df is not None:
            data = Data(cached_df.copy(), symbol=symbol, timeframe=timeframe)
            data._source_name = source_name
            full_params = dict(params)
            full_params["symbol"] = symbol
            if timeframe:
                full_params["timeframe"] = timeframe
            data._fetch_params = full_params
            return data

    df = fetcher()
    if cache:
        DataCache.set(source_name, cache_payload, df)

    data = Data(df, symbol=symbol, timeframe=timeframe)
    data._source_name = source_name
    # Ensure symbol and timeframe are in params for future updates
    full_params = dict(params)
    full_params["symbol"] = symbol
    if timeframe:
        full_params["timeframe"] = timeframe
    data._fetch_params = full_params
    return data


def _filter_symbols(symbols: List[str], pattern: Optional[str]) -> List[str]:
    """Filter symbols using glob or regex."""
    if not pattern:
        return sorted(list(set(symbols)))
    
    # Try glob first
    if "*" in pattern or "?" in pattern:
        filtered = fnmatch.filter(symbols, pattern)
    else:
        # Try regex
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            filtered = [s for s in symbols if regex.search(s)]
        except re.error:
            # Fallback to simple contains
            filtered = [s for s in symbols if pattern.lower() in s.lower()]
    
    return sorted(list(set(filtered)))


class Data:
    """Wrapper class for trading data, mimicking VectorBT's Data object."""
    
    def __init__(self, df: pd.DataFrame, symbol: Optional[Union[str, List[str]]] = None, timeframe: Optional[str] = None):
        self._df = df
        self._symbol = symbol
        self._timeframe = timeframe
        self._source_name = None
        self._fetch_params = {}

    def get(self, column: str = "close") -> Union[pd.Series, pd.DataFrame]:
        """Get a specific column from the data."""
        col = column.lower()
        
        # Handle MultiIndex columns (VBT style)
        if isinstance(self._df.columns, pd.MultiIndex):
            # Find the level that contains OHLCV columns (usually the last one)
            for level in range(self._df.columns.nlevels - 1, -1, -1):
                level_vals = [str(v).lower() for v in self._df.columns.get_level_values(level).unique()]
                if col in level_vals:
                    # We need to find the actual case-sensitive value in the level
                    actual_val = None
                    for v in self._df.columns.get_level_values(level).unique():
                        if str(v).lower() == col:
                            actual_val = v
                            break
                    return self._df.xs(actual_val, axis=1, level=level)

        if col in self._df.columns:
            return self._df[col]
            
        # Try to find a match if exact lowercase fails
        for c in self._df.columns:
            if str(c).lower() == col:
                return self._df[c]
        raise ValueError(f"Column '{column}' not found in data. Available: {list(self._df.columns)}")

    @property
    def close(self) -> Union[pd.Series, pd.DataFrame]:
        return self.get("close")

    @property
    def open(self) -> Union[pd.Series, pd.DataFrame]:
        return self.get("open")

    @property
    def high(self) -> Union[pd.Series, pd.DataFrame]:
        return self.get("high")

    @property
    def low(self) -> Union[pd.Series, pd.DataFrame]:
        return self.get("low")

    @property
    def volume(self) -> Union[pd.Series, pd.DataFrame]:
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
        symbol: Union[str, List[str]],
        timeframe: str = "H1",
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        count: Optional[int] = None,
        cache: bool = False,
        classes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Data:
        """Download data from MT5."""
        from backend.services.market_data.data_getters import load_mt5

        symbols = [symbol] if isinstance(symbol, str) else symbol

        def fetcher() -> pd.DataFrame:
            dfs = {}
            for sym in symbols:
                df = load_mt5(
                    symbol=sym,
                    timeframe=timeframe,
                    start_date=start,
                    end_date=end,
                    count=count or 0,
                    **kwargs
                )
                if df is not None and not df.empty:
                    dfs[sym] = df
            
            if not dfs:
                raise ValueError(f"Failed to download any MT5 data for {symbols}")
            
            if len(dfs) == 1 and not classes:
                return next(iter(dfs.values()))
            
            # Combine into MultiIndex DataFrame
            # Base level: Symbol
            # Second level: Column (open, high, etc.)
            combined = pd.concat(dfs.values(), axis=1, keys=dfs.keys())
            
            if classes:
                # Add classes as top-level MultiIndex
                # e.g. {"EURUSD": {"sector": "USDPairs"}}
                first_meta = next(iter(classes.values()))
                if isinstance(first_meta, dict):
                    # We add levels in reverse so the first key in the dict is level 0
                    for meta_key in reversed(list(first_meta.keys())):
                        new_columns = []
                        for col_tuple in combined.columns:
                            # The symbol is always second to last in (..., sym, col)
                            sym = col_tuple[-2] if len(col_tuple) > 1 else col_tuple[0]
                            val = classes.get(sym, {}).get(meta_key, "Unknown")
                            new_columns.append((val,) + col_tuple)
                        combined.columns = pd.MultiIndex.from_tuples(new_columns)
                
            return combined

        return _download_with_cache(
            source_name="MT5Data",
            symbol=symbol,
            timeframe=timeframe,
            cache=cache,
            params={
                "start": start, 
                "end": end, 
                "count": count or 0, 
                "classes": classes,
                **kwargs
            },
            fetcher=fetcher,
        )

    @staticmethod
    def list_symbols(pattern: Optional[str] = None) -> List[str]:
        """List available symbols in MT5."""
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return []
            symbols = [s.name for s in mt5.symbols_get()]
            return _filter_symbols(symbols, pattern)
        except Exception:
            return []


class DukascopyData:
    """Data source for Dukascopy."""
    
    @staticmethod
    def download(
        symbol: str,
        timeframe: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        count: Optional[int] = None,
        cache: bool = False,
        **kwargs
    ) -> Data:
        """Download data from Dukascopy API."""
        from backend.services.market_data.data_getters import load_dukascopy

        def fetcher() -> pd.DataFrame:
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
            return df

        return _download_with_cache(
            source_name="DukascopyData",
            symbol=symbol,
            timeframe=timeframe,
            cache=cache,
            params={"start": start, "end": end, "count": count, **kwargs},
            fetcher=fetcher,
        )

    @staticmethod
    def list_symbols(pattern: Optional[str] = None) -> List[str]:
        """List available symbols in Dukascopy."""
        try:
            from backend.services.market_data.dukascopy_instruments import INSTRUMENT_MAP
            symbols = list(INSTRUMENT_MAP.keys())
            return _filter_symbols(symbols, pattern)
        except Exception:
            return []


class YFData:
    """Data source for Yahoo Finance."""
    
    @staticmethod
    def download(
        symbol: Union[str, List[str]],
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        period: Optional[str] = None,
        interval: str = "1d",
        cache: bool = False,
        **kwargs
    ) -> Data:
        """Download data from Yahoo Finance."""
        def fetcher() -> pd.DataFrame:
            try:
                import yfinance as yf
            except ImportError:
                raise ImportError(
                    "yfinance is required for YFData. Install with 'pip install yfinance'"
                )

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

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.set_levels(
                    [level.lower() for level in df.columns.levels[0]],
                    level=0,
                )
            else:
                df.columns = [str(column).lower() for column in df.columns]
            return df

        return _download_with_cache(
            source_name="YFData",
            symbol=symbol,
            timeframe=interval,
            cache=cache,
            params={
                "start": start,
                "end": end,
                "period": period,
                "interval": interval,
                **kwargs,
            },
            fetcher=fetcher,
        )


class BinanceData:
    """Data source for Binance."""
    
    @staticmethod
    def download(
        symbol: str,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None,
        interval: str = "1d",
        cache: bool = False,
        **kwargs
    ) -> Data:
        """Download data from Binance."""
        def fetcher() -> pd.DataFrame:
            try:
                from binance import Client
            except ImportError:
                raise ImportError(
                    "python-binance is required for BinanceData. Install with 'pip install python-binance'"
                )

            client = Client(None, None)
            request_start = start
            request_end = end

            if isinstance(request_start, datetime):
                request_start = request_start.strftime("%d %b %Y %H:%M:%S")
            if isinstance(request_end, datetime):
                request_end = request_end.strftime("%d %b %Y %H:%M:%S")

            klines = client.get_historical_klines(
                symbol,
                interval,
                request_start,
                request_end,
            )

            cols = [
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ]
            df = pd.DataFrame(klines, columns=cols)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col])
            return df

        return _download_with_cache(
            source_name="BinanceData",
            symbol=symbol,
            timeframe=interval,
            cache=cache,
            params={"start": start, "end": end, "interval": interval, **kwargs},
            fetcher=fetcher,
        )

    @staticmethod
    def list_symbols(pattern: Optional[str] = None) -> List[str]:
        """List available symbols in Binance."""
        try:
            from binance import Client
            client = Client(None, None)
            exchange_info = client.get_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols']]
            return _filter_symbols(symbols, pattern)
        except Exception:
            return []


class CCXTData:
    """Data source for CCXT (supports many exchanges)."""
    
    @staticmethod
    def download(
        symbol: str,
        exchange: str = "binance",
        start: Optional[Union[str, datetime]] = None,
        timeframe: str = "1d",
        limit: int = 1000,
        cache: bool = False,
        **kwargs
    ) -> Data:
        """Download data using CCXT."""
        def fetcher() -> pd.DataFrame:
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
            return df

        return _download_with_cache(
            source_name="CCXTData",
            symbol=symbol,
            timeframe=timeframe,
            cache=cache,
            params={
                "exchange": exchange,
                "start": start,
                "timeframe": timeframe,
                "limit": limit,
                **kwargs,
            },
            fetcher=fetcher,
        )


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
            
        # Map MT5-style interval to Pandas freq
        freq = _map_timeframe(interval)
        date_range = pd.date_range(start=start, end=end, freq=freq)
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
        
        return Data(df, symbol=symbols, timeframe=interval)


class CSVData:
    """Data source for CSV files."""
    
    @staticmethod
    def load(
        path: Union[str, Path],
        index_col: Union[int, str] = 0,
        parse_dates: bool = True,
        **kwargs
    ) -> Data:
        """Load data from a CSV file."""
        df = pd.read_csv(path, index_col=index_col, parse_dates=parse_dates, **kwargs)
        # Normalize columns to lowercase
        df.columns = [str(c).lower() for c in df.columns]
        return Data(df, symbol=Path(path).stem)


class ParquetData:
    """Data source for Parquet files."""
    
    @staticmethod
    def load(
        path: Union[str, Path],
        **kwargs
    ) -> Data:
        """Load data from a Parquet file."""
        df = pd.read_parquet(path, **kwargs)
        # Normalize columns to lowercase
        df.columns = [str(c).lower() for c in df.columns]
        return Data(df, symbol=Path(path).stem)


class DataSaver:
    """Base class for saving and periodically updating data."""
    
    def __init__(self, data: Data, path: Optional[Union[str, Path]] = None):
        self.data = data
        self._path = path

    def _get_extension(self) -> str:
        raise NotImplementedError

    @property
    def path(self) -> Path:
        if self._path:
            return Path(self._path)
        folder = Path(PROJECT_ROOT) / "backend" / "data" / "saved"
        folder.mkdir(parents=True, exist_ok=True)
        sym = str(self.data._symbol).replace("/", "_").replace(" ", "_")
        tf = self.data._timeframe or "unknown"
        return folder / f"{sym}_{tf}.{self._get_extension()}"

    @property
    def meta_path(self) -> Path:
        return self.path.with_suffix(".json")

    @classmethod
    def file_exists(cls, path: Optional[Union[str, Path]] = None, symbol: str = "EURUSD", timeframe: str = "M1") -> bool:
        if path:
            return os.path.exists(path)
        # Check default location
        folder = Path(PROJECT_ROOT) / "backend" / "data" / "saved"
        ext = cls(Data(pd.DataFrame(), symbol=symbol, timeframe=timeframe))._get_extension()
        path = folder / f"{symbol}_{timeframe}.{ext}"
        return path.exists()

    def save(self, is_initial: bool = False):
        """Save data and source metadata."""
        # Save metadata
        meta = {
            "symbol": self.data._symbol,
            "timeframe": self.data._timeframe,
            "source_name": self.data._source_name,
            "fetch_params": self.data._fetch_params
        }
        with open(self.meta_path, "w") as f:
            json.dump(meta, f, default=str)
        self._save_df()
        
        if is_initial:
            start_str = self.data.df.index[0].strftime("%Y-%m-%d %H:%M:%S") if not self.data.df.empty else "N/A"
            end_str = self.data.df.index[-1].strftime("%Y-%m-%d %H:%M:%S") if not self.data.df.empty else "N/A"
            print(f"INFO:haruquant.data.saver:Saved initial {len(self.data.df)} rows from {start_str} to {end_str}")

    def _save_df(self):
        raise NotImplementedError

    @classmethod
    def load(cls, path: Optional[Union[str, Path]] = None, symbol: str = "EURUSD", timeframe: str = "M1") -> "DataSaver":
        """Load data and source metadata."""
        if not path:
            folder = Path(PROJECT_ROOT) / "backend" / "data" / "saved"
            ext = cls(Data(pd.DataFrame(), symbol=symbol, timeframe=timeframe))._get_extension()
            path = folder / f"{symbol}_{timeframe}.{ext}"
            
        path = Path(path)
        meta_path = path.with_suffix(".json")
        if not path.exists() or not meta_path.exists():
            raise FileNotFoundError(f"Data or metadata not found at {path}")
            
        with open(meta_path, "r") as f:
            meta = json.load(f)
            
        df = cls._load_df(path)
        data = Data(df, symbol=meta["symbol"], timeframe=meta["timeframe"])
        data._source_name = meta["source_name"]
        data._fetch_params = meta["fetch_params"]
        return cls(data, path=path)

    @staticmethod
    def _load_df(path: Path) -> pd.DataFrame:
        raise NotImplementedError

    def update(self) -> int:
        """Fetch latest data using stored source info. Returns number of new rows."""
        if not self.data._source_name:
             print("Warning: Data object has no source information. Skipping update.")
             return 0
        
        source_cls = getattr(sys.modules[__name__], self.data._source_name)
        
        params = dict(self.data._fetch_params)
        start_time = None
        if not self.data.df.empty:
             start_time = self.data.df.index[-1]
             params["start"] = start_time
             if "count" in params and params["count"]:
                  params["count"] = max(params["count"], 10)
        
        try:
            new_data = source_cls.download(**params)
            
            if new_data.df.empty:
                return 0
                
            prev_len = len(self.data.df)
            combined = pd.concat([self.data.df, new_data.df])
            self.data._df = combined[~combined.index.duplicated(keep='last')].sort_index()
            
            new_rows = len(self.data.df) - prev_len
            if new_rows > 0:
                start_str = start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else "N/A"
                end_str = self.data.df.index[-1].strftime("%Y-%m-%d %H:%M:%S")
                print(f"INFO:haruquant.data.saver:Saved {new_rows} rows from {start_str} to {end_str}")
            return new_rows
        except Exception as e:
            # print(f"Update failed for {self.data._symbol}: {e}")
            return 0

    def update_every(self, interval: int, unit: str = "minute", init_save: bool = True):
        """Start periodic updates (blocking)."""
        import time
        from datetime import datetime, timedelta
        
        if init_save:
            self.save(is_initial=True)
            
        seconds = interval
        if unit == "minute": delta = timedelta(minutes=interval); seconds *= 60
        elif unit == "hour": delta = timedelta(hours=interval); seconds *= 3600
        elif unit == "day": delta = timedelta(days=interval); seconds *= 86400
        else: delta = timedelta(minutes=interval); seconds *= 60
        
        next_run = datetime.now() + delta
        print(f"INFO:haruquant.utils.schedule_:Starting schedule manager with jobs [Every {interval} {unit} do update() (last run: [never], next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')})]")
        
        try:
            while True:
                time.sleep(seconds)
                self.update()
                self.save()
        except KeyboardInterrupt:
            print("INFO:haruquant.utils.schedule_:Stopping schedule manager")


class CSVDataSaver(DataSaver):
    def _get_extension(self) -> str:
        return "csv"

    def _save_df(self):
        self.data.df.to_csv(self.path)

    @staticmethod
    def _load_df(path: Path) -> pd.DataFrame:
        return pd.read_csv(path, index_col=0, parse_dates=True)


class ParquetDataSaver(DataSaver):
    def _get_extension(self) -> str:
        return "parquet"

    def _save_df(self):
        self.data.df.to_parquet(self.path)

    @staticmethod
    def _load_df(path: Path) -> pd.DataFrame:
        return pd.read_parquet(path)


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
            


class DataSplitter:
    """Utilities for data splitting and preparation."""
    
    @staticmethod
    def rolling_split(
        data: Union[pd.Series, pd.DataFrame, Data],
        window_len: int,
        set_lens: tuple = (1, 1),
        left_to_right: bool = False,
        step: int = 1,
    ) -> List[dict]:
        """
        Perform a rolling split of the data into training and testing sets.
        Mimics vbt.rolling_split.
        
        Args:
            data: The data to split.
            window_len: Total length of the window (train + test).
            set_lens: Relative lengths of (train, test) or (train, valid, test).
            left_to_right: Direction of the rolling window.
            step: Number of bars to step the window forward.
            
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
            indices = range(0, n - window_len + 1, step)
        else:
            indices = range(n - window_len, -1, -step)
            
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
