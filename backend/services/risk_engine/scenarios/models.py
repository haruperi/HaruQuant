"""Scenario contracts for risk stress analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class StressScenario:
    """One deterministic stress scenario definition."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioResult:
    """One evaluated scenario result."""

    name: str
    loss: float
    stressed_var: float | None = None
    stressed_es: float | None = None
    context: Dict[str, Any] = field(default_factory=dict)
