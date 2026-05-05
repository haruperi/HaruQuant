"""Deterministic baseline strategies for benchmark comparisons."""

from services.strategy.baselines.ema_cross import EmaCrossBaselineStrategy
from services.strategy.baselines.naive_momentum import NaiveMomentumStrategy
from services.strategy.baselines.rsi import RsiBaselineStrategy

__all__ = [
    "EmaCrossBaselineStrategy",
    "NaiveMomentumStrategy",
    "RsiBaselineStrategy",
]
