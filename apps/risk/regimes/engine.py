"""Canonical regime engine for portfolio risk state."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from apps.risk.metrics.math import build_returns_df
from apps.risk.models import PortfolioState

from .crisis_regime import CrisisRegimeDetector
from .liquidity_regime import LiquidityRegimeDetector
from .market_regime import MarketRegimeDetector
from .models import RegimeReport, RegimeState
from .regime_transition import build_regime_transition
from .volatility_regime import VolatilityRegimeDetector


class RegimeEngine:
    """Aggregate market, volatility, liquidity, and crisis regime state."""

    def __init__(
        self,
        crisis_detector: Optional[CrisisRegimeDetector] = None,
        market_detector: Optional[MarketRegimeDetector] = None,
        volatility_detector: Optional[VolatilityRegimeDetector] = None,
        liquidity_detector: Optional[LiquidityRegimeDetector] = None,
    ):
        self.crisis_detector = crisis_detector or CrisisRegimeDetector()
        self.market_detector = market_detector or MarketRegimeDetector()
        self.volatility_detector = volatility_detector or VolatilityRegimeDetector()
        self.liquidity_detector = liquidity_detector or LiquidityRegimeDetector()

    def evaluate_state(
        self,
        state: PortfolioState,
        previous: Optional[RegimeState] = None,
        equity_curve: Optional[pd.Series] = None,
    ) -> RegimeReport:
        """Build one aggregate regime report from canonical portfolio state."""
        returns_df = build_returns_df(state)
        equity_series = _normalize_equity_curve_input(equity_curve)
        if equity_series is None:
            equity_series = _equity_curve_from_state(state)

        crisis_state, signals = self.crisis_detector.detect_with_signals(returns_df, equity_series)
        market_state = self.market_detector.detect(returns_df)
        volatility_state = self.volatility_detector.detect(returns_df)
        liquidity_state = self.liquidity_detector.detect(state)

        aggregate = RegimeState(
            name=crisis_state.name,
            family="aggregate",
            confidence=crisis_state.confidence,
            signals_triggered=list(crisis_state.signals_triggered),
            warnings=list(crisis_state.warnings)
            + _subregime_warnings(market_state, volatility_state, liquidity_state),
            metadata={
                "market_regime": market_state.name,
                "volatility_regime": volatility_state.name,
                "liquidity_regime": liquidity_state.name,
            },
        )
        transition = build_regime_transition(previous, aggregate)
        return RegimeReport(
            current=aggregate,
            market=market_state,
            volatility=volatility_state,
            liquidity=liquidity_state,
            crisis=crisis_state,
            transition=transition,
            signals=signals,
        )


class RiskRegimeDetector(CrisisRegimeDetector):
    """Compatibility detector that preserves the legacy detect() interface."""


def _equity_curve_from_state(state: PortfolioState) -> Optional[pd.Series]:
    equity_curve = state.metadata.get("equity_curve")
    if isinstance(equity_curve, pd.Series):
        return equity_curve
    if isinstance(equity_curve, list) and equity_curve:
        return pd.Series(equity_curve, dtype=float)
    return None


def _normalize_equity_curve_input(equity_curve: Any) -> Optional[pd.Series]:
    if equity_curve is None:
        return None
    if isinstance(equity_curve, pd.Series):
        return equity_curve.astype(float)
    if isinstance(equity_curve, list):
        if not equity_curve:
            return None
        values = []
        for item in equity_curve:
            if isinstance(item, dict):
                value = item.get("equity")
            else:
                value = getattr(item, "equity", None)
            if value is None:
                continue
            values.append(float(value))
        return pd.Series(values, dtype=float) if values else None
    return None


def _subregime_warnings(*states: RegimeState) -> list[str]:
    warnings: list[str] = []
    for state in states:
        if state.name in {"UNKNOWN", "NORMAL", "NORMAL_VOL", "DIVERSIFIED"}:
            continue
        warnings.append(f"{state.family} regime: {state.name}")
    return warnings
