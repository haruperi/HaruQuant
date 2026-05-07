"""Standard labels used by Research Department agents."""

from __future__ import annotations

from enum import Enum


class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class VolatilityRegime(str, Enum):
    COMPRESSED = "compressed"
    NORMAL = "normal"
    ELEVATED = "elevated"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class LiquidityRegime(str, Enum):
    GOOD = "good"
    NORMAL = "normal"
    THIN = "thin"
    IMPAIRED = "impaired"
    UNKNOWN = "unknown"
