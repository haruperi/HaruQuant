"""Base contracts for normalized risk scorecards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from services.risk.metrics import RiskSnapshot


@dataclass(frozen=True)
class ScoreRow:
    """One normalized score row suitable for later persistence."""

    family: str
    score_key: str
    score_value: float
    confidence: float = 0.0
    confidence_label: str = "low"
    explanation: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreContext:
    """Execution context for one scorecard run."""

    snapshot: RiskSnapshot
    shared: Dict[str, Any] = field(default_factory=dict)


class ScoreFamily(Protocol):
    """Family-level score calculator contract."""

    family_name: str

    def compute(self, context: ScoreContext) -> List[ScoreRow]:
        """Compute normalized score rows for this family."""


@dataclass(frozen=True)
class RiskScorecard:
    """Scorecard built from a normalized risk snapshot."""

    snapshot: RiskSnapshot
    score_rows: List[ScoreRow]
    summary: Dict[str, Any] = field(default_factory=dict)
