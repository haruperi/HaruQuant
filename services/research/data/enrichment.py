"""Dataset enrichment for Edge Lab analysis-ready OHLCVS frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from services.research.session_config import active_sessions_for_hour

from .models import CanonicalOHLCVSSchema


@dataclass(frozen=True)
class EnrichmentConfig:
    """Configuration for deterministic dataset enrichment."""

    symbol: str = ""
    pip_size: Optional[float] = None
    point_size: Optional[float] = None
    rollover_hour_utc: int = 21
    session_basis: str = "dataset_index"


def _infer_pip_size(symbol: str) -> float:
    symbol_upper = symbol.upper()
    if "JPY" in symbol_upper:
        return 0.01
    if symbol_upper:
        return 0.0001
    return 1.0

def enrich_dataset(
    df: pd.DataFrame,
    *,
    schema: CanonicalOHLCVSSchema | None = None,
    config: EnrichmentConfig | None = None,
) -> pd.DataFrame:
    """Add pip metadata, bar geometry, returns, labels, and calendar/session fields."""
    schema = schema or CanonicalOHLCVSSchema()
    config = config or EnrichmentConfig()

    out = df.copy()
    pip_size = float(config.pip_size or _infer_pip_size(config.symbol))
    point_size = float(config.point_size or min(pip_size / 10.0, pip_size))

    out["pip_size"] = pip_size
    out["point_size"] = point_size

    body = out[schema.close] - out[schema.open]
    bar_range = out[schema.high] - out[schema.low]
    upper_wick = out[schema.high] - out[[schema.open, schema.close]].max(axis=1)
    lower_wick = out[[schema.open, schema.close]].min(axis=1) - out[schema.low]

    out["body_pips"] = body / pip_size
    out["range_pips"] = bar_range / pip_size
    out["upper_wick_pips"] = upper_wick / pip_size
    out["lower_wick_pips"] = lower_wick / pip_size

    out["returns"] = out[schema.close].pct_change()
    out["log_returns"] = np.log(out[schema.close] / out[schema.close].shift(1))

    out["bar_direction"] = np.where(
        out[schema.close] > out[schema.open],
        "up",
        np.where(out[schema.close] < out[schema.open], "down", "flat"),
    )

    out["hour"] = out.index.hour
    out["weekday"] = out.index.dayofweek
    out["month"] = out.index.month
    out["quarter"] = out.index.quarter

    active_sessions = out["hour"].map(active_sessions_for_hour)
    out["active_sessions"] = active_sessions.map(lambda values: ",".join(values))
    out["session_label"] = active_sessions.map(
        lambda values: "_".join(values) if values else "gap"
    )
    out["session"] = out["session_label"]
    out["is_overlap"] = active_sessions.map(lambda values: len(values) > 1)
    out["is_gap"] = active_sessions.map(lambda values: len(values) == 0)
    out["is_rollover_hour"] = out["hour"] == int(config.rollover_hour_utc)
    out["session_basis"] = str(config.session_basis)

    return out
