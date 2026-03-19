"""Market regime classification for portfolio-level risk state."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .models import RegimeState


class MarketRegimeDetector:
    """Classify market fragility from broad portfolio return behavior."""

    def __init__(self, lookback: int = 60, corr_fragile_level: float = 0.55):
        self.lookback = lookback
        self.corr_fragile_level = corr_fragile_level

    def detect(self, returns_df: pd.DataFrame) -> RegimeState:
        if returns_df is None or returns_df.empty or returns_df.shape[0] < self.lookback:
            return RegimeState(name="UNKNOWN", family="market", warnings=["Insufficient market returns history."])

        r = returns_df.dropna().iloc[-self.lookback :]
        if r.empty:
            return RegimeState(name="UNKNOWN", family="market", warnings=["No valid returns after filtering."])
        if r.shape[1] < 2:
            return RegimeState(name="SINGLE_ASSET", family="market", confidence=1.0)

        corr = r.corr()
        off = corr.values.copy()
        np.fill_diagonal(off, np.nan)
        avg_off = float(np.nanmean(off))
        if avg_off >= self.corr_fragile_level:
            return RegimeState(
                name="FRAGILE",
                family="market",
                confidence=min(avg_off / max(self.corr_fragile_level, 1e-9), 1.0),
                metadata={"average_correlation": avg_off},
            )
        return RegimeState(
            name="DIVERSIFIED",
            family="market",
            confidence=max(0.0, 1.0 - avg_off),
            metadata={"average_correlation": avg_off},
        )
