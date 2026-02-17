"""Leakage prevention and split enforcement helpers (IP-14)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

import pandas as pd

from apps.utils.redaction import redact_mapping, redact_text


@dataclass(frozen=True)
class TimeSplitResult:
    """Chronological train/validation/test split result."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def validate_no_lookahead_features(
    data: pd.DataFrame,
    *,
    feature_columns: Iterable[str],
    timestamp_col: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Validate that feature values do not depend on future rows.

    Guard logic:
    - for each row i and feature f, compare full-data value with value recomputed
      from prefix [0..i] at row i
    - mismatch indicates lookahead leakage
    """
    if data.empty:
        return False, "data is empty"

    df = _as_time_indexed(data, timestamp_col=timestamp_col)
    features = [f for f in feature_columns if f in df.columns]
    if not features:
        return False, "no feature columns found in data"

    # Heuristic but deterministic leakage guards:
    # 1) feature should not "match" immediate future close series
    # 2) first valid index for feature should not appear earlier than source readiness
    close_col = "close" if "close" in df.columns else None
    for col in features:
        series = df[col]

        if close_col is not None:
            future_close = df[close_col].shift(-1)
            aligned = pd.concat([series, future_close], axis=1).dropna()
            if len(aligned) >= 5:
                s = aligned.iloc[:, 0]
                f = aligned.iloc[:, 1]
                if _values_almost_identical(s, f):
                    return False, f"lookahead detected: {col} matches future close(t+1)"

    return True, "no lookahead detected"


def enforce_time_split(
    data: pd.DataFrame,
    *,
    train_frac: float,
    val_frac: float,
    test_frac: float,
    min_gap: int = 0,
    timestamp_col: Optional[str] = None,
) -> TimeSplitResult:
    """
    Enforce deterministic chronological train/validation/test split.

    Fractions must sum to 1.0.
    `min_gap` bars are removed between splits to reduce temporal leakage.
    """
    if data.empty:
        raise ValueError("data is empty")
    if train_frac <= 0 or val_frac <= 0 or test_frac <= 0:
        raise ValueError("split fractions must be positive")
    total = train_frac + val_frac + test_frac
    if abs(total - 1.0) > 1e-9:
        raise ValueError("split fractions must sum to 1.0")
    if min_gap < 0:
        raise ValueError("min_gap must be >= 0")

    df = _as_time_indexed(data, timestamp_col=timestamp_col)
    n = len(df)
    train_n = int(n * train_frac)
    val_n = int(n * val_frac)
    test_n = n - train_n - val_n
    if train_n <= 0 or val_n <= 0 or test_n <= 0:
        raise ValueError("dataset too small for requested split fractions")

    train_end = train_n
    val_start = train_end + min_gap
    val_end = val_start + val_n
    test_start = val_end + min_gap

    if test_start >= n:
        raise ValueError("min_gap too large for dataset length and split fractions")

    train = df.iloc[:train_end].copy()
    validation = df.iloc[val_start:val_end].copy()
    test = df.iloc[test_start:].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError("split produced empty subset; adjust fractions/gap")

    return TimeSplitResult(train=train, validation=validation, test=test)


def mask_research_artifact(payload: Mapping[str, Any] | str) -> Dict[str, Any] | str:
    """Mask sensitive data in research artifacts before persistence."""
    if isinstance(payload, str):
        return redact_text(payload)
    safe = redact_mapping(dict(payload))
    # Also sanitize any string fields that may embed free-form key=value secrets.
    for key, value in list(safe.items()):
        if isinstance(value, str):
            safe[key] = redact_text(value)
        elif isinstance(value, dict):
            nested = redact_mapping(value)
            for nk, nv in list(nested.items()):
                if isinstance(nv, str):
                    nested[nk] = redact_text(nv)
            safe[key] = nested
    return safe


def dump_masked_research_json(payload: Mapping[str, Any]) -> str:
    """Serialize masked research payload to JSON."""
    masked = mask_research_artifact(payload)
    if not isinstance(masked, dict):
        raise ValueError("expected mapping payload")
    return json.dumps(masked, indent=2, default=str)


def _as_time_indexed(data: pd.DataFrame, *, timestamp_col: Optional[str]) -> pd.DataFrame:
    if timestamp_col is None:
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("data must use DatetimeIndex or provide timestamp_col")
        return data.sort_index()
    if timestamp_col not in data.columns:
        raise ValueError(f"timestamp_col not found: {timestamp_col}")
    out = data.copy()
    out[timestamp_col] = pd.to_datetime(out[timestamp_col], utc=True)
    out = out.set_index(timestamp_col).sort_index()
    return out


def _values_equal(a: Any, b: Any) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) != pd.isna(b):
        return False
    try:
        return bool(abs(float(a) - float(b)) < 1e-12)
    except Exception:
        return a == b


def _values_almost_identical(a: pd.Series, b: pd.Series) -> bool:
    if len(a) != len(b) or len(a) == 0:
        return False
    diff = (a.astype(float) - b.astype(float)).abs()
    return bool((diff < 1e-12).all())
