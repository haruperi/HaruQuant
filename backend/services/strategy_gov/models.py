"""Strategy governance domain models."""

from __future__ import annotations

from enum import StrEnum


class StrategyLifecycleState(StrEnum):
    RESEARCH = "RESEARCH"
    BACKTEST_QUALIFIED = "BACKTEST_QUALIFIED"
    ROBUSTNESS_QUALIFIED = "ROBUSTNESS_QUALIFIED"
    PAPER_APPROVED = "PAPER_APPROVED"
    LIVE_LIMITED = "LIVE_LIMITED"
    LIVE_PRODUCTION = "LIVE_PRODUCTION"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"

