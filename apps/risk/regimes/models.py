"""Normalized regime models for portfolio risk state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RegimeSignal:
    """One explainable regime signal observation."""

    signal_key: str
    triggered: bool
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None
    message: str = ""


@dataclass(frozen=True)
class RegimeState:
    """Normalized regime state used across risk analytics and governance."""

    name: str
    family: str = "aggregate"
    confidence: float = 0.0
    signals_triggered: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_stress(self) -> bool:
        return str(self.name).upper() == "STRESS"


@dataclass(frozen=True)
class RegimeTransition:
    """Simple transition metadata between two regime states."""

    changed: bool
    previous_name: Optional[str] = None
    current_name: Optional[str] = None


@dataclass(frozen=True)
class RegimeReport:
    """Aggregate regime report produced by the regime engine."""

    current: RegimeState
    market: RegimeState
    volatility: RegimeState
    liquidity: RegimeState
    crisis: RegimeState
    transition: RegimeTransition
    signals: List[RegimeSignal] = field(default_factory=list)
