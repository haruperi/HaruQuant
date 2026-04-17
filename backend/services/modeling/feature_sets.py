"""Reusable feature-set builders for unsupervised modeling workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class FeatureSetFrame:
    """Serializable result of building a feature set from source market data."""

    name: str
    version: str
    frame: pd.DataFrame
    feature_columns: tuple[str, ...]
    metadata: dict[str, Any]

    def to_metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "feature_columns": list(self.feature_columns),
            **self.metadata,
        }


def build_market_regime_feature_frame(
    data: pd.DataFrame,
    *,
    fast_period: int = 20,
    slow_period: int = 50,
    volatility_window: int = 20,
    momentum_window: int = 5,
    min_periods: int = 3,
    include_ema_spread: bool = True,
    price_column: str = "close",
) -> FeatureSetFrame:
    """Build timestamp-aligned features for PCA/K-Means regime research."""
    if data.empty:
        raise ValueError("data must contain at least one row")
    if price_column not in data.columns:
        raise ValueError(f"missing price column: {price_column}")

    frame = data.copy()
    close = pd.to_numeric(frame[price_column], errors="coerce")
    high = pd.to_numeric(frame.get("high", close), errors="coerce")
    low = pd.to_numeric(frame.get("low", close), errors="coerce")

    frame["return_1"] = close.pct_change()
    frame["rolling_volatility"] = frame["return_1"].rolling(
        window=volatility_window,
        min_periods=min_periods,
    ).std()
    frame["momentum"] = close.pct_change(periods=momentum_window)
    frame["range_pct"] = (high - low) / close.replace(0, pd.NA)

    feature_columns: list[str] = [
        "return_1",
        "rolling_volatility",
        "momentum",
        "range_pct",
    ]
    fast_col = f"ema_{fast_period}"
    slow_col = f"ema_{slow_period}"
    if include_ema_spread and fast_col in frame.columns and slow_col in frame.columns:
        frame["ema_spread"] = (
            pd.to_numeric(frame[fast_col], errors="coerce")
            - pd.to_numeric(frame[slow_col], errors="coerce")
        ) / close.replace(0, pd.NA)
        feature_columns.append("ema_spread")

    research_columns = ["open", "high", "low", price_column, *feature_columns]
    available_columns = [column for column in research_columns if column in frame.columns]
    feature_frame = frame.loc[:, available_columns].replace([pd.NA], float("nan"))
    feature_frame = feature_frame.dropna(subset=feature_columns)

    metadata = {
        "price_column": price_column,
        "source_rows": int(len(data)),
        "rows_after_dropna": int(len(feature_frame)),
        "fast_period": fast_period,
        "slow_period": slow_period,
        "volatility_window": volatility_window,
        "momentum_window": momentum_window,
        "include_ema_spread": bool(include_ema_spread and fast_col in frame.columns and slow_col in frame.columns),
        "available_columns": [str(column) for column in available_columns],
    }
    return FeatureSetFrame(
        name="market_regime_core",
        version="1.0.0",
        frame=feature_frame,
        feature_columns=tuple(feature_columns),
        metadata=metadata,
    )


__all__ = [
    "FeatureSetFrame",
    "build_market_regime_feature_frame",
]
