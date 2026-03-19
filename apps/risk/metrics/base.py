"""Base contracts for normalized risk metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from apps.risk.models import PortfolioState


@dataclass(frozen=True)
class MetricRow:
    """One normalized metric row suitable for later persistence."""

    family: str
    metric_key: str
    scope: str
    scope_key: Optional[str] = None
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    unit: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricContext:
    """Execution context for one metric registry run."""

    state: PortfolioState
    shared: Dict[str, Any] = field(default_factory=dict)


class MetricFamily(Protocol):
    """Family-level metric calculator contract."""

    family_name: str

    def compute(self, context: MetricContext) -> List[MetricRow]:
        """Compute normalized metric rows for this family."""


@dataclass(frozen=True)
class RiskSnapshot:
    """Current-state risk snapshot built from normalized metric rows."""

    state: PortfolioState
    metric_rows: List[MetricRow]
    summary: Dict[str, Any] = field(default_factory=dict)
