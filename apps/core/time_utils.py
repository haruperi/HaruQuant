"""Shared clock and freshness helpers for migration-era services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from apps.utils.datetime_utils import parse_datetime


UTC = timezone.utc


class Clock(Protocol):
    """Minimal clock protocol used by workflow and TTL-sensitive services."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""


class SystemClock:
    """Clock implementation backed by the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedClock:
    """Deterministic clock for tests and replay-sensitive code."""

    current: datetime

    def now(self) -> datetime:
        return _to_utc(self.current)


def _to_utc(value: Any) -> datetime:
    parsed = parse_datetime(value, assume_tz="UTC")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class FreshnessWindow:
    """A freshness result derived from an observed timestamp and a TTL."""

    observed_at: datetime
    checked_at: datetime
    max_age_seconds: int

    @property
    def age_seconds(self) -> float:
        return max((self.checked_at - self.observed_at).total_seconds(), 0.0)

    @property
    def expires_at(self) -> datetime:
        return self.observed_at + timedelta(seconds=self.max_age_seconds)

    @property
    def is_fresh(self) -> bool:
        return self.age_seconds <= float(self.max_age_seconds)

    @property
    def is_stale(self) -> bool:
        return not self.is_fresh


def evaluate_freshness(
    observed_at: Any,
    *,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> FreshnessWindow:
    """Evaluate whether a timestamp is still fresh under a TTL window."""

    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")

    active_clock = clock or SystemClock()
    return FreshnessWindow(
        observed_at=_to_utc(observed_at),
        checked_at=_to_utc(active_clock.now()),
        max_age_seconds=int(max_age_seconds),
    )


def is_stale(
    observed_at: Any,
    *,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> bool:
    """Return True when the observed timestamp is older than the TTL window."""

    return evaluate_freshness(
        observed_at,
        max_age_seconds=max_age_seconds,
        clock=clock,
    ).is_stale
