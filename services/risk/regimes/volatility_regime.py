"""Volatility regime classification for portfolio risk state."""

from __future__ import annotations

import pandas as pd

from .models import RegimeState


class VolatilityRegimeDetector:
    """Classify realized volatility state from returns history."""

    def __init__(self, lookback: int = 60, high_vol_mult: float = 1.35, low_vol_mult: float = 0.75):
        self.lookback = lookback
        self.high_vol_mult = high_vol_mult
        self.low_vol_mult = low_vol_mult

    def detect(self, returns_df: pd.DataFrame) -> RegimeState:
        if returns_df is None or returns_df.empty or returns_df.shape[0] < self.lookback:
            return RegimeState(name="UNKNOWN", family="volatility", warnings=["Insufficient returns history."])

        r = returns_df.dropna().iloc[-self.lookback :]
        port = r.mean(axis=1)
        vol_now = float(port.std())
        median_vol = float(port.rolling(max(10, min(self.lookback, 20))).std().median())
        if median_vol <= 0.0:
            return RegimeState(name="UNKNOWN", family="volatility", warnings=["Volatility baseline unavailable."])

        ratio = vol_now / median_vol
        if ratio >= self.high_vol_mult:
            return RegimeState(
                name="HIGH_VOL",
                family="volatility",
                confidence=min((ratio - 1.0) / max(self.high_vol_mult - 1.0, 1e-9), 1.0),
                metadata={"vol_ratio": ratio, "vol_now": vol_now, "median_vol": median_vol},
            )
        if ratio <= self.low_vol_mult:
            return RegimeState(
                name="LOW_VOL",
                family="volatility",
                confidence=min((1.0 - ratio) / max(1.0 - self.low_vol_mult, 1e-9), 1.0),
                metadata={"vol_ratio": ratio, "vol_now": vol_now, "median_vol": median_vol},
            )
        return RegimeState(
            name="NORMAL_VOL",
            family="volatility",
            confidence=max(0.0, 1.0 - abs(ratio - 1.0)),
            metadata={"vol_ratio": ratio, "vol_now": vol_now, "median_vol": median_vol},
        )
