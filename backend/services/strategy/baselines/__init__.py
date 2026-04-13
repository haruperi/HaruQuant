"""Deterministic baseline strategies for benchmark comparisons."""

from backend.services.strategy.baselines.ema_cross import EmaCrossBaselineStrategy
from backend.services.strategy.baselines.naive_momentum import NaiveMomentumStrategy
from backend.services.strategy.baselines.rsi import RsiBaselineStrategy

__all__ = [
    "EmaCrossBaselineStrategy",
    "NaiveMomentumStrategy",
    "RsiBaselineStrategy",
]
