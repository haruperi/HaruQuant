from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
_EXAMPLE_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "market_data"
_EXAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ======================================================================
# Display helpers
# ======================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any, indent: int = 2) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}")
        for k, v in value.items():
            print(f"{prefix}  {k:<28s} {v}")
    elif isinstance(value, list):
        print(f"{prefix}{label}")
        for item in value:
            print(f"{prefix}  - {item}")
    else:
        print(f"{prefix}{label:<30s} {value}")


# ======================================================================
# Shared sample data for file-based examples
# ======================================================================


def _build_sample_ohlcv(n_bars: int = 200) -> pd.DataFrame:
    closes = [1.1000 + i * 0.0003 + (0.0005 if i % 7 == 0 else 0) for i in range(n_bars)]
    idx = pd.date_range("2025-01-02", periods=n_bars, freq="h", tz="UTC")
    return pd.DataFrame({
        "open": closes,
        "high": [c + 0.0010 for c in closes],
        "low": [c - 0.0010 for c in closes],
        "close": closes,
        "volume": [100 + i * 2 for i in range(n_bars)],
    }, index=idx)


def _ensure_sample_csv() -> Path:
    filepath = _EXAMPLE_DATA_DIR / "eurusd_sample.csv"
    if not filepath.exists():
        df = _build_sample_ohlcv()
        df.reset_index().rename(columns={"index": "timestamp"}).to_csv(filepath, index=False)
    return filepath


def _ensure_sample_parquet() -> Path:
    filepath = _EXAMPLE_DATA_DIR / "eurusd_sample.parquet"
    if not filepath.exists():
        _build_sample_ohlcv().to_parquet(filepath)
    return filepath


def _load_market_data(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 14,
) -> Optional[pd.DataFrame]:
    """Load OHLCV from MT5 (falls back to Dukascopy)."""
    from backend.services.market_data.data_getters import load_mt5

    if start_date is None:
        end_date = end_date or datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

    df = load_mt5(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
    )
    return df if df is not None and not df.empty else None


# ======================================================================
# Example 01 – 04: Data loading (each uses its own source)
# ======================================================================

def example_01_load_mt5() -> None:
    """Load OHLCV data from MetaTrader 5 (falls back to Dukascopy)."""
    print_header("Example 01: Load Market Data — MT5")
    from backend.services.market_data.data_getters import load_mt5

    symbol, timeframe = "XAUUSD", "H1"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    print_kv("Source", "MetaTrader 5")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print_kv("Date range", f"{start_date.date()} → {end_date.date()}")
    print()

    try:
        df = load_mt5(symbol=symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        if df is None:
            from backend.services.market_data.data_getters import load_dukascopy
            df = load_dukascopy(
                symbol=symbol, timeframe=timeframe,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        if isinstance(df.index, pd.DatetimeIndex) and len(df):
            print_kv("Date range", f"{df.index[0]} → {df.index[-1]}")
        print_kv("Columns", list(df.columns))
        print()
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_02_load_dukascopy() -> None:
    """Load OHLCV data from Dukascopy HTTP API."""
    print_header("Example 02: Load Market Data — Dukascopy")
    from backend.services.market_data.data_getters import load_dukascopy

    print_kv("Source", "Dukascopy HTTP API")
    print_kv("Symbol", "EURUSD")
    print_kv("Date range", "2025-06-01 → 2025-06-08")
    print()
    try:
        df = load_dukascopy(symbol="EURUSD", timeframe="H1", start_date="2025-06-01", end_date="2025-06-08")
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_03_load_parquet() -> None:
    """Load OHLCV data from a local Parquet file."""
    print_header("Example 03: Load Market Data — Parquet")
    from backend.services.market_data.data_getters import load_parquet

    filepath = _ensure_sample_parquet()
    print_kv("File", str(filepath))
    print()
    try:
        df = load_parquet(filepath)
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_04_load_csv() -> None:
    """Load OHLCV data from CSV via CSVDataSource."""
    print_header("Example 04: Load Market Data — CSV (CSVDataSource)")
    from backend.services.market_data.data_getters import CSVDataSource

    filepath = _ensure_sample_csv()
    print_kv("File", str(filepath))
    print()
    try:
        source = CSVDataSource(filepath)
        df = source.fetch_data(symbol="EURUSD", timeframe="H1", start_pos=0, end_pos=50)
        if df is None:
            print("  ❌ No data returned.")
            return
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


# ======================================================================
# Example 05: Full data-preprocess pipeline (MT5 → validate → clean → enrich)
# ======================================================================

def example_05_data_preprocess() -> None:
    """Load from MT5 and run through validate → clean → enrich pipeline."""
    print_header("Example 05: Data Preprocessing — Full Pipeline")
    from backend.services.research.datasets import normalize_columns, prepare_ohlcvs_dataset

    symbol, timeframe = "EURUSD", "H1"
    print_kv("Source", "MT5 → validate → clean → enrich")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print()

    raw_df = _load_market_data(symbol=symbol, timeframe=timeframe)
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    print(f"  ✅ Step 1: Loaded {len(raw_df)} raw bars from MT5\n")

    class _InMemoryDataSource:
        def __init__(self, df):
            self._df = df
        def fetch_data(self, symbol, timeframe, start_pos, end_pos):
            if start_pos < 0 or end_pos > len(self._df) or start_pos >= end_pos:
                return None
            return self._df.iloc[start_pos:end_pos].copy()

    normalized = normalize_columns(raw_df)
    source = _InMemoryDataSource(normalized)

    try:
        dataset = prepare_ohlcvs_dataset(
            source=source, symbol=symbol, timeframe=timeframe,
            start_pos=0, end_pos=min(500, len(normalized)),
        )
        print("  ✅ Step 3: Full pipeline completed\n")
        print_kv("Dataset summary", "")
        print_kv("  rows", len(dataset.data))
        print_kv("  columns", list(dataset.data.columns))
        print_kv("  is_valid", dataset.report.is_valid)
        print_kv("  warnings", len(dataset.report.warnings))
        print_kv("  fatal errors", len(dataset.report.fatal_errors))
        print()
        print(dataset.data.head(3).to_string())
        print()
    except ValueError as exc:
        print(f"  ⚠️  Validation failed: {exc}")


if __name__ == "__main__":
    example_01_load_mt5()
    example_02_load_dukascopy()
    example_03_load_parquet()
    example_04_load_csv()
    example_05_data_preprocess()