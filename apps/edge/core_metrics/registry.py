"""Registry for Edge Core Metric calculators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .base import MetricCalculator


@dataclass
class MetricRegistry:
    """Small registry keyed by metric family."""

    _calculators: Dict[str, MetricCalculator] = field(default_factory=dict)

    def register(self, calculator: MetricCalculator) -> None:
        self._calculators[calculator.family] = calculator

    def get(self, family: str) -> MetricCalculator:
        return self._calculators[family]

    def all(self) -> List[MetricCalculator]:
        return [self._calculators[key] for key in sorted(self._calculators)]

    def families(self) -> List[str]:
        return sorted(self._calculators)

    @classmethod
    def from_calculators(
        cls, calculators: Iterable[MetricCalculator]
    ) -> "MetricRegistry":
        registry = cls()
        for calculator in calculators:
            registry.register(calculator)
        return registry
