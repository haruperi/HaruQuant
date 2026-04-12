"""Liquidity regime classification for portfolio risk state."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from backend.services.risk_engine.models import PortfolioState

from .models import RegimeState


class LiquidityRegimeDetector:
    """Classify liquidity regime from spread burden proxies in market slices."""

    def __init__(self, stressed_spread_bps: float = 12.0, wide_spread_bps: float = 5.0):
        self.stressed_spread_bps = stressed_spread_bps
        self.wide_spread_bps = wide_spread_bps

    def detect(self, state: PortfolioState) -> RegimeState:
        spread_bps = self._spread_bps_by_symbol(state)
        if not spread_bps:
            return RegimeState(name="UNKNOWN", family="liquidity", warnings=["No spread data available."])

        avg_spread_bps = sum(spread_bps.values()) / len(spread_bps)
        if avg_spread_bps >= self.stressed_spread_bps:
            return RegimeState(
                name="STRESSED",
                family="liquidity",
                confidence=min(avg_spread_bps / max(self.stressed_spread_bps, 1e-9), 1.0),
                metadata={"average_spread_bps": avg_spread_bps, "spread_bps_by_symbol": spread_bps},
            )
        if avg_spread_bps >= self.wide_spread_bps:
            return RegimeState(
                name="WIDE",
                family="liquidity",
                confidence=min(avg_spread_bps / max(self.stressed_spread_bps, 1e-9), 1.0),
                metadata={"average_spread_bps": avg_spread_bps, "spread_bps_by_symbol": spread_bps},
            )
        return RegimeState(
            name="NORMAL",
            family="liquidity",
            confidence=max(0.0, 1.0 - (avg_spread_bps / max(self.wide_spread_bps, 1e-9))),
            metadata={"average_spread_bps": avg_spread_bps, "spread_bps_by_symbol": spread_bps},
        )

    def _spread_bps_by_symbol(self, state: PortfolioState) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for symbol, market in state.markets.items():
            bars = market.bars
            if bars is None or bars.empty:
                continue
            spread_col = "Spread" if "Spread" in bars.columns else "spread" if "spread" in bars.columns else None
            close_col = "Close" if "Close" in bars.columns else "close" if "close" in bars.columns else None
            if spread_col is None or close_col is None:
                continue
            last_spread = float(bars[spread_col].iloc[-1])
            last_close = float(bars[close_col].iloc[-1])
            if last_close <= 0.0:
                continue
            out[symbol] = float((last_spread / last_close) * 10000.0)
        return out
