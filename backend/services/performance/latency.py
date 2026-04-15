"""Latency budget monitoring helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.common.logger import logger

@dataclass(frozen=True)
class LatencySample:
    operation: str
    latency_ms: int


@dataclass(frozen=True)
class LatencyAlert:
    operation: str
    threshold_ms: int
    observed_latency_ms: int


class LatencyBudgetMonitor:
    """Raise alerts when observed latency exceeds a configured budget."""

    def __init__(self, *, threshold_ms: int) -> None:
        self._threshold_ms = threshold_ms

    def evaluate(self, sample: LatencySample) -> LatencyAlert | None:
        if sample.latency_ms <= self._threshold_ms:
            return None
        return LatencyAlert(
            operation=sample.operation,
            threshold_ms=self._threshold_ms,
            observed_latency_ms=sample.latency_ms,
        )

    def evaluate_many(self, samples: tuple[LatencySample, ...]) -> tuple[LatencyAlert, ...]:
        return tuple(alert for sample in samples if (alert := self.evaluate(sample)) is not None)
