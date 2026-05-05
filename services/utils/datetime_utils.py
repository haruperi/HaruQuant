"""Date/time and timezone normalization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Union
from zoneinfo import ZoneInfo


OutputType = Literal["iso", "datetime", "epoch_s", "epoch_ms"]


def _resolve_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception as exc:
        raise ValueError(f"Invalid timezone: {tz_name}") from exc


def _is_epoch_milliseconds(value: Union[int, float]) -> bool:
    return abs(float(value)) >= 1_000_000_000_000


def parse_datetime(value: Any, assume_tz: str = "UTC") -> datetime:
    """
    Parse datetime input into timezone-aware datetime.

    Supported input types:
    - datetime
    - ISO-8601 string (supports trailing 'Z')
    - unix epoch seconds/ms (int/float)
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        seconds = float(value) / 1000.0 if _is_epoch_milliseconds(value) else float(value)
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Datetime string cannot be empty")
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Unsupported datetime format: {value}") from exc
    else:
        raise ValueError(f"Unsupported datetime value type: {type(value).__name__}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_resolve_tz(assume_tz))
    return dt


def to_utc(dt: datetime, assume_tz: str = "UTC") -> datetime:
    """Normalize datetime to timezone-aware UTC."""
    parsed = parse_datetime(dt, assume_tz=assume_tz)
    return parsed.astimezone(timezone.utc)


def to_naive_utc(dt: datetime, assume_tz: str = "UTC") -> datetime:
    """Normalize datetime to UTC and drop tzinfo."""
    return to_utc(dt, assume_tz=assume_tz).replace(tzinfo=None)


def normalize_timestamp(
    value: Any,
    *,
    output: OutputType = "iso",
    assume_tz: str = "UTC",
) -> Union[str, datetime, int]:
    """Normalize an input timestamp to a desired output representation."""
    dt_utc = parse_datetime(value, assume_tz=assume_tz).astimezone(timezone.utc)

    if output == "datetime":
        return dt_utc
    if output == "epoch_s":
        return int(dt_utc.timestamp())
    if output == "epoch_ms":
        return int(dt_utc.timestamp() * 1000.0)
    if output == "iso":
        return dt_utc.isoformat().replace("+00:00", "Z")

    raise ValueError(f"Unsupported output format: {output}")


def normalize_timezone_for_series(
    series_or_index: Any,
    *,
    target_tz: str = "UTC",
    make_naive: bool = False,
) -> Any:
    """
    Normalize pandas DatetimeIndex/Series timezone.

    - Naive values are localized to UTC before conversion.
    - Aware values are converted to target timezone.
    - If make_naive=True, timezone info is removed at the end.
    """
    import pandas as pd

    tz = _resolve_tz(target_tz)

    if isinstance(series_or_index, pd.DatetimeIndex):
        out = series_or_index
        if out.tz is None:
            out = out.tz_localize("UTC")
        out = out.tz_convert(tz)
        return out.tz_localize(None) if make_naive else out

    if isinstance(series_or_index, pd.Series):
        if not isinstance(series_or_index.dtype, pd.DatetimeTZDtype):
            out = pd.to_datetime(series_or_index, errors="raise")
            if out.dt.tz is None:
                out = out.dt.tz_localize("UTC")
        else:
            out = series_or_index
        out = out.dt.tz_convert(tz)
        return out.dt.tz_localize(None) if make_naive else out

    raise ValueError("normalize_timezone_for_series expects pandas Series or DatetimeIndex")

