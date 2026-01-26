"""
Market data utilities for the simulator.

Provides simple storage and retrieval of ticks and bars to support
tester-mode data access without MT5 calls.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

import MetaTrader5 as mt5
import pandas as pd


def ensure_utc(value: datetime) -> datetime:
    """Ensure a datetime is timezone-aware in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_symbol(symbol: str) -> bool:
    """Ensure symbol exists and is selected in MarketWatch."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return False
    if not info.visible:
        return bool(mt5.symbol_select(symbol, True))
    return True


def timeframe_seconds(timeframe: int) -> int:
    """Return timeframe length in seconds."""
    mapping = {
        mt5.TIMEFRAME_M1: 60,
        mt5.TIMEFRAME_M2: 120,
        mt5.TIMEFRAME_M3: 180,
        mt5.TIMEFRAME_M4: 240,
        mt5.TIMEFRAME_M5: 300,
        mt5.TIMEFRAME_M6: 360,
        mt5.TIMEFRAME_M10: 600,
        mt5.TIMEFRAME_M12: 720,
        mt5.TIMEFRAME_M15: 900,
        mt5.TIMEFRAME_M20: 1200,
        mt5.TIMEFRAME_M30: 1800,
        mt5.TIMEFRAME_H1: 3600,
        mt5.TIMEFRAME_H2: 7200,
        mt5.TIMEFRAME_H3: 10800,
        mt5.TIMEFRAME_H4: 14400,
        mt5.TIMEFRAME_H6: 21600,
        mt5.TIMEFRAME_H8: 28800,
        mt5.TIMEFRAME_H12: 43200,
        mt5.TIMEFRAME_D1: 86400,
        mt5.TIMEFRAME_W1: 604800,
        mt5.TIMEFRAME_MN1: 2592000,
    }
    return mapping.get(timeframe, 0)


def timeframe_label(timeframe: int) -> str:
    """Return a readable timeframe label for storage paths."""
    mapping = {
        mt5.TIMEFRAME_M1: "M1",
        mt5.TIMEFRAME_M2: "M2",
        mt5.TIMEFRAME_M3: "M3",
        mt5.TIMEFRAME_M4: "M4",
        mt5.TIMEFRAME_M5: "M5",
        mt5.TIMEFRAME_M6: "M6",
        mt5.TIMEFRAME_M10: "M10",
        mt5.TIMEFRAME_M12: "M12",
        mt5.TIMEFRAME_M15: "M15",
        mt5.TIMEFRAME_M20: "M20",
        mt5.TIMEFRAME_M30: "M30",
        mt5.TIMEFRAME_H1: "H1",
        mt5.TIMEFRAME_H2: "H2",
        mt5.TIMEFRAME_H3: "H3",
        mt5.TIMEFRAME_H4: "H4",
        mt5.TIMEFRAME_H6: "H6",
        mt5.TIMEFRAME_H8: "H8",
        mt5.TIMEFRAME_H12: "H12",
        mt5.TIMEFRAME_D1: "D1",
        mt5.TIMEFRAME_W1: "W1",
        mt5.TIMEFRAME_MN1: "MN1",
    }
    return mapping.get(timeframe, str(timeframe))


def _rates_to_dicts(rates: Any) -> list[dict[str, Any]]:
    if rates is None:
        return []
    if isinstance(rates, list):
        return [dict(row) if isinstance(row, dict) else dict(row) for row in rates]
    if getattr(rates, "dtype", None) is None or rates.dtype.names is None:
        return []
    return [
        {
            name: r[name].item() if hasattr(r[name], "item") else r[name]
            for name in rates.dtype.names
        }
        for r in rates
    ]


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_end(value: datetime) -> datetime:
    start = _month_start(value)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return next_month


def _iter_months(start: datetime, end: datetime) -> Iterable[datetime]:
    current = _month_start(start)
    end_month = _month_start(end)
    while current <= end_month:
        yield current
        current = _month_end(current)


class MarketDataStore:
    """Persist ticks and bars to disk for tester-mode playback."""

    def __init__(self, base_dir: str = "data/market_data") -> None:
        """Initialize storage paths for ticks and bars."""
        self.base_dir = base_dir
        self.ticks_dir = os.path.join(base_dir, "ticks")
        self.bars_dir = os.path.join(base_dir, "bars")
        os.makedirs(self.ticks_dir, exist_ok=True)
        os.makedirs(self.bars_dir, exist_ok=True)

    def _ticks_path(self, symbol: str, month_key: str) -> str:
        folder = os.path.join(self.ticks_dir, symbol)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{month_key}.parquet")

    def _bars_path(self, symbol: str, timeframe: int, month_key: str) -> str:
        tf_label = timeframe_label(timeframe)
        folder = os.path.join(self.bars_dir, symbol, tf_label)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{month_key}.parquet")

    def fetch_ticks_range(
        self, symbol: str, start_time: datetime, end_time: datetime, flags: int
    ) -> list[dict[str, Any]]:
        """Fetch ticks from MT5 and store them to disk."""
        if not ensure_symbol(symbol):
            return []
        start_time = ensure_utc(start_time)
        end_time = ensure_utc(end_time)
        ticks = mt5.copy_ticks_range(symbol, start_time, end_time, flags)
        data = _rates_to_dicts(ticks)
        if data:
            self._store_ticks(symbol, data)
        return data

    def read_ticks_range(
        self, symbol: str, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        """Read ticks from disk for the requested date range."""
        start_time = ensure_utc(start_time)
        end_time = ensure_utc(end_time)
        rows: list[dict[str, Any]] = []
        for month in _iter_months(start_time, end_time):
            path = self._ticks_path(symbol, _month_key(month))
            if not os.path.exists(path):
                continue
            df = pd.read_parquet(path)
            rows.extend(df.to_dict(orient="records"))
        return self._filter_time(rows, start_time, end_time)

    def fetch_bars_range(
        self,
        symbol: str,
        timeframe: int,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch bars from MT5 and store them to disk."""
        if not ensure_symbol(symbol):
            return []
        start_time = ensure_utc(start_time)
        end_time = ensure_utc(end_time)
        rates = mt5.copy_rates_range(symbol, timeframe, start_time, end_time)
        data = _rates_to_dicts(rates)
        if data:
            self._store_bars(symbol, timeframe, data)
        return data

    def read_bars_range(
        self,
        symbol: str,
        timeframe: int,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Read bars from disk for the requested date range."""
        start_time = ensure_utc(start_time)
        end_time = ensure_utc(end_time)
        rows: list[dict[str, Any]] = []
        for month in _iter_months(start_time, end_time):
            path = self._bars_path(symbol, timeframe, _month_key(month))
            if not os.path.exists(path):
                continue
            df = pd.read_parquet(path)
            rows.extend(df.to_dict(orient="records"))
        return self._filter_time(rows, start_time, end_time)

    def _store_ticks(self, symbol: str, data: list[dict[str, Any]]) -> None:
        if not data:
            return
        df = pd.DataFrame(data)
        if "time" not in df.columns:
            return
        for month_key in (
            df["time"]
            .apply(
                lambda t: _month_key(datetime.fromtimestamp(int(t), tz=timezone.utc))
            )
            .unique()
        ):
            path = self._ticks_path(symbol, month_key)
            subset = df[
                df["time"].apply(
                    lambda t: _month_key(
                        datetime.fromtimestamp(int(t), tz=timezone.utc)
                    )
                )
                == month_key
            ]
            self._merge_parquet(
                path, subset, "time_msc" if "time_msc" in subset else "time"
            )

    def _store_bars(
        self, symbol: str, timeframe: int, data: list[dict[str, Any]]
    ) -> None:
        if not data:
            return
        df = pd.DataFrame(data)
        if "time" not in df.columns:
            return
        for month_key in (
            df["time"]
            .apply(
                lambda t: _month_key(datetime.fromtimestamp(int(t), tz=timezone.utc))
            )
            .unique()
        ):
            path = self._bars_path(symbol, timeframe, month_key)
            subset = df[
                df["time"].apply(
                    lambda t: _month_key(
                        datetime.fromtimestamp(int(t), tz=timezone.utc)
                    )
                )
                == month_key
            ]
            self._merge_parquet(path, subset, "time")

    def _merge_parquet(self, path: str, df: pd.DataFrame, key: str) -> None:
        if os.path.exists(path):
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df
        if key in combined.columns:
            combined = combined.drop_duplicates(subset=[key])
        combined = combined.sort_values(by=key)
        combined.to_parquet(path, index=False)

    def _filter_time(
        self,
        rows: list[dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        result = []
        for row in rows:
            time_value = row.get("time")
            if time_value is None:
                continue
            try:
                ts = int(time_value)
            except (TypeError, ValueError):
                continue
            if start_ts <= ts <= end_ts:
                result.append(row)
        return result
