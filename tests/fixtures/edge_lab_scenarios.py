from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class ScenarioDataSource:
    registry: Dict[str, pd.DataFrame]

    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_pos: int,
        end_pos: int,
    ) -> pd.DataFrame:
        if symbol not in self.registry:
            raise KeyError(f"Unknown synthetic symbol: {symbol}")
        return self.registry[symbol].copy()


def _frame(
    index: pd.DatetimeIndex,
    close: np.ndarray,
    *,
    spread: np.ndarray | float,
    volume: np.ndarray | float,
    range_scale: np.ndarray | float,
) -> pd.DataFrame:
    open_ = np.concatenate(([close[0]], close[:-1]))
    scale = np.asarray(range_scale if isinstance(range_scale, np.ndarray) else np.full(len(index), range_scale), dtype=float)
    high = np.maximum(open_, close) + scale
    low = np.minimum(open_, close) - scale
    spread_values = np.asarray(spread if isinstance(spread, np.ndarray) else np.full(len(index), spread), dtype=float)
    volume_values = np.asarray(volume if isinstance(volume, np.ndarray) else np.full(len(index), volume), dtype=float)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume_values,
            "Spread": spread_values,
        },
        index=index,
    )


def trending_df() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=240, freq="h")
    base = np.linspace(1.10, 1.18, len(index))
    pullbacks = 0.0015 * np.sin(np.arange(len(index)) / 3.0)
    close = base + pullbacks
    range_scale = np.where((index.hour >= 10) & (index.hour <= 16), 0.0012, 0.0007)
    return _frame(index, close, spread=8.0, volume=180.0, range_scale=range_scale)


def ranging_df() -> pd.DataFrame:
    index = pd.date_range("2024-02-01", periods=240, freq="h")
    center = 1.205
    close = center + 0.004 * np.sin(np.arange(len(index)) / 4.0)
    range_scale = np.where((index.hour >= 10) & (index.hour <= 16), 0.0008, 0.0006)
    return _frame(index, close, spread=9.0, volume=140.0, range_scale=range_scale)


def noisy_df() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    index = pd.date_range("2024-03-01", periods=240, freq="h")
    close = 1.300 + np.cumsum(rng.normal(0.0, 0.0016, len(index)))
    range_scale = np.full(len(index), 0.0012)
    return _frame(index, close, spread=11.0, volume=130.0, range_scale=range_scale)


def spread_heavy_df() -> pd.DataFrame:
    index = pd.date_range("2024-04-01", periods=180, freq="h")
    close = 1.420 + 0.0012 * np.sin(np.arange(len(index)) / 2.5)
    range_scale = np.full(len(index), 0.00045)
    spread = np.full(len(index), 28.0)
    return _frame(index, close, spread=spread, volume=95.0, range_scale=range_scale)


def missing_data_df() -> pd.DataFrame:
    df = trending_df().iloc[:180].copy()
    df = df.drop(df.index[20:28])
    df.loc[df.index[40], "Volume"] = np.nan
    df.loc[df.index[60], "Spread"] = np.nan
    return df


def short_history_df() -> pd.DataFrame:
    return ranging_df().iloc[:18].copy()


def dst_boundary_df() -> pd.DataFrame:
    first = pd.date_range("2024-10-26 18:00:00", periods=10, freq="h")
    second = pd.DatetimeIndex(
        [
            "2024-10-27 02:00:00",
            "2024-10-27 02:00:00",
            "2024-10-27 03:00:00",
            "2024-10-27 04:00:00",
            "2024-10-27 05:00:00",
            "2024-10-27 06:00:00",
            "2024-10-27 07:00:00",
            "2024-10-27 08:00:00",
            "2024-10-27 09:00:00",
            "2024-10-27 10:00:00",
        ]
    )
    index = first.append(second)
    close = 1.255 + 0.002 * np.sin(np.arange(len(index)) / 2.0)
    range_scale = np.where((pd.Index(index.hour) >= 2) & (pd.Index(index.hour) <= 8), 0.0008, 0.0005)
    return _frame(index, close, spread=10.0, volume=120.0, range_scale=range_scale)


def build_edge_lab_scenario_registry() -> Dict[str, pd.DataFrame]:
    return {
        "TRENDUSD": trending_df(),
        "RANGEUSD": ranging_df(),
        "NOISYUSD": noisy_df(),
        "SPREADUSD": spread_heavy_df(),
        "MISSUSD": missing_data_df(),
        "SHORTUSD": short_history_df(),
        "DSTUSD": dst_boundary_df(),
    }
