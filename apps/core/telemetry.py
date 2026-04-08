"""Minimal telemetry helpers for migration-era services."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, Iterator, List, Tuple


Attributes = Dict[str, Any]
MetricKey = Tuple[str, Tuple[Tuple[str, str], ...]]


def _freeze_attributes(attributes: Attributes | None) -> Tuple[Tuple[str, str], ...]:
    if not attributes:
        return ()
    return tuple(sorted((str(key), str(value)) for key, value in attributes.items()))


@dataclass(frozen=True)
class TelemetryEvent:
    """A structured telemetry event emitted by a service."""

    name: str
    attributes: Attributes = field(default_factory=dict)


@dataclass(frozen=True)
class CounterMetric:
    """A simple increment-only metric snapshot."""

    name: str
    value: int
    attributes: Attributes = field(default_factory=dict)


@dataclass(frozen=True)
class TimerMetric:
    """A recorded duration metric snapshot."""

    name: str
    duration_ms: float
    attributes: Attributes = field(default_factory=dict)


@dataclass(frozen=True)
class SpanRecord:
    """A recorded span with timing and attributes."""

    name: str
    duration_ms: float
    attributes: Attributes = field(default_factory=dict)


class InMemoryTelemetry:
    """In-process telemetry collector for early migration services and tests."""

    def __init__(self) -> None:
        self._events: List[TelemetryEvent] = []
        self._counters: Dict[MetricKey, int] = {}
        self._timers: List[TimerMetric] = []
        self._spans: List[SpanRecord] = []

    def emit_event(self, name: str, **attributes: Any) -> TelemetryEvent:
        event = TelemetryEvent(name=name, attributes=dict(attributes))
        self._events.append(event)
        return event

    def increment(self, name: str, value: int = 1, **attributes: Any) -> CounterMetric:
        key = (name, _freeze_attributes(attributes))
        self._counters[key] = self._counters.get(key, 0) + value
        return CounterMetric(name=name, value=self._counters[key], attributes=dict(attributes))

    def record_duration(self, name: str, duration_ms: float, **attributes: Any) -> TimerMetric:
        metric = TimerMetric(name=name, duration_ms=float(duration_ms), attributes=dict(attributes))
        self._timers.append(metric)
        return metric

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[SpanRecord]:
        started = perf_counter()
        try:
            yield SpanRecord(name=name, duration_ms=0.0, attributes=dict(attributes))
        finally:
            duration_ms = (perf_counter() - started) * 1000.0
            self._spans.append(
                SpanRecord(name=name, duration_ms=duration_ms, attributes=dict(attributes))
            )

    @property
    def events(self) -> List[TelemetryEvent]:
        return list(self._events)

    @property
    def counters(self) -> List[CounterMetric]:
        return [
            CounterMetric(name=name, value=value, attributes=dict(attrs))
            for (name, attrs), value in self._counters.items()
        ]

    @property
    def timers(self) -> List[TimerMetric]:
        return list(self._timers)

    @property
    def spans(self) -> List[SpanRecord]:
        return list(self._spans)
