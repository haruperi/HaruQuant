"""Canonical normalization for MT5 ZeroMQ and Dukascopy payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ProgressCallback = Callable[[int, int, float], None]


class CanonicalTick(BaseModel):
    """Canonical tick schema."""

    model_config = ConfigDict(extra="allow")

    provider: str = "mt5_ea"
    schema_version: str = "1.0"
    symbol: str = Field(min_length=1)
    timestamp: datetime
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    last: Optional[float] = Field(default=None, gt=0)
    volume: float = Field(ge=0, default=0.0)
    sequence: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator("ask")
    @classmethod
    def _ask_ge_bid(cls, ask: float, info: Any) -> float:
        bid = info.data.get("bid")
        if bid is not None and ask < bid:
            raise ValueError("ask must be greater than or equal to bid")
        return ask


class CanonicalBar(BaseModel):
    """Canonical bar schema."""

    model_config = ConfigDict(extra="allow")

    provider: str = "mt5_ea"
    schema_version: str = "1.0"
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0, default=0.0)
    sequence: Optional[int] = Field(default=None, ge=0)
    source: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator("high")
    @classmethod
    def _high_ge_low(cls, high: float, info: Any) -> float:
        low = info.data.get("low")
        if low is not None and high < low:
            raise ValueError("high must be greater than or equal to low")
        return high

    @field_validator("close")
    @classmethod
    def _close_within_hl(cls, close: float, info: Any) -> float:
        high = info.data.get("high")
        low = info.data.get("low")
        if high is not None and low is not None and (close > high or close < low):
            raise ValueError("close must be within [low, high]")
        return close


def normalize_mt5_tick(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize provider tick payload into canonical tick dict."""
    canonical = CanonicalTick.model_validate(
        {
            "provider": payload.get("provider", "mt5_ea"),
            "schema_version": payload.get("schema_version", "1.0"),
            "symbol": payload.get("symbol"),
            "timestamp": payload.get("event_time_utc") or payload.get("timestamp"),
            "bid": payload.get("bid"),
            "ask": payload.get("ask"),
            "last": payload.get("last"),
            "volume": payload.get("volume", 0.0),
            "sequence": payload.get("sequence"),
            "source": payload.get("source"),
        }
    )
    return canonical.model_dump()


def normalize_mt5_bar(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize provider bar payload into canonical bar dict."""
    canonical = CanonicalBar.model_validate(
        {
            "provider": payload.get("provider", "mt5_ea"),
            "schema_version": payload.get("schema_version", "1.0"),
            "symbol": payload.get("symbol"),
            "timeframe": payload.get("timeframe"),
            "timestamp": payload.get("event_time_utc") or payload.get("timestamp"),
            "open": payload.get("open"),
            "high": payload.get("high"),
            "low": payload.get("low"),
            "close": payload.get("close"),
            "volume": payload.get("volume", 0.0),
            "sequence": payload.get("sequence"),
            "source": payload.get("source"),
        }
    )
    return canonical.model_dump()


def normalize_mt5_event(payload: Mapping[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Normalize event payload and return (canonical, error)."""
    event_type = str(payload.get("type", "")).lower()
    try:
        if event_type == "tick":
            return normalize_mt5_tick(payload), None
        if event_type == "bar":
            return normalize_mt5_bar(payload), None
        if event_type in {"heartbeat", "status"}:
            return dict(payload), None
        return None, f"unsupported event type: {event_type}"
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {"msg": str(exc), "loc": []}
        loc = ".".join(str(x) for x in first.get("loc", []))
        msg = first.get("msg", "validation error")
        return None, f"{loc}: {msg}" if loc else msg


def normalize_dukascopy_bar(
    row: Mapping[str, Any],
    symbol: str,
    timeframe: str,
    timestamp: Any,
    sequence: Optional[int] = None,
) -> Dict[str, Any]:
    """Normalize one Dukascopy OHLCV row to canonical bar dict."""
    canonical = CanonicalBar.model_validate(
        {
            "provider": "dukascopy",
            "schema_version": "1.0",
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": timestamp,
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volume": row.get("volume", 0.0),
            "sequence": sequence,
            "source": "dukascopy",
        }
    )
    return canonical.model_dump()


def normalize_dukascopy_dataframe(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> list[Dict[str, Any]]:
    """Normalize Dukascopy OHLC dataframe into canonical bar records."""
    if df.empty:
        return []
    total = len(df)
    records: list[Dict[str, Any]] = []
    for idx, (ts, row) in enumerate(df.iterrows(), start=1):
        rec = normalize_dukascopy_bar(row, symbol=symbol, timeframe=timeframe, timestamp=ts, sequence=idx)
        records.append(rec)
        if progress_callback is not None:
            progress_callback(idx, total, (idx / total) * 100.0)
    return records
