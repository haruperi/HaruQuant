"""Deterministic Dukascopy market-data normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from services.utils.time_utils import Clock, FreshnessWindow, evaluate_freshness

from .quality import DataValidator


@dataclass(frozen=True)
class DukascopyBarsSnapshot:
    """Normalized Dukascopy bars with freshness metadata."""

    symbol: str
    timeframe: str
    bars: pd.DataFrame
    observed_at: datetime
    max_age_seconds: int
    source: str = "dukascopy"

    @property
    def row_count(self) -> int:
        return int(len(self.bars))

    @property
    def start_at(self) -> datetime | None:
        if self.bars.empty:
            return None
        return _to_utc_timestamp(self.bars.index[0])

    @property
    def end_at(self) -> datetime | None:
        if self.bars.empty:
            return None
        return _to_utc_timestamp(self.bars.index[-1])

    def freshness(self, *, clock: Clock | None = None) -> FreshnessWindow:
        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=clock,
        )

    def to_payload(self, *, include_bars: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source": self.source,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "row_count": self.row_count,
            "observed_at": _format_timestamp(self.observed_at),
            "max_age_seconds": self.max_age_seconds,
            "start_at": _format_timestamp(self.start_at),
            "end_at": _format_timestamp(self.end_at),
        }
        if include_bars:
            payload["bars"] = _bars_to_records(self.bars)
        return payload


def normalize_dukascopy_bars(
    bars: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    observed_at: datetime | None = None,
    max_age_seconds: int = 86_400,
) -> DukascopyBarsSnapshot:
    """Normalize raw Dukascopy OHLCV bars to backend market-data shape."""

    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")
    if bars.empty:
        raise ValueError("Dukascopy returned no bars")

    normalized = DataValidator.prepare_data(bars)
    observed = observed_at or datetime.now(UTC)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)

    return DukascopyBarsSnapshot(
        symbol=symbol.upper(),
        timeframe=timeframe.upper(),
        bars=normalized,
        observed_at=observed.astimezone(UTC),
        max_age_seconds=int(max_age_seconds),
    )


def _to_utc_timestamp(value: Any) -> datetime:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.to_pydatetime().astimezone(UTC)


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _bars_to_records(bars: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for timestamp, row in bars.iterrows():
        record = {
            "timestamp": _format_timestamp(_to_utc_timestamp(timestamp)),
        }
        record.update({column: row[column] for column in bars.columns})
        records.append(record)
    return records


__all__ = [
    "DukascopyBarsSnapshot",
    "normalize_dukascopy_bars",
]
