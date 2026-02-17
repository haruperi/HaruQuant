"""Dukascopy historical adapter with canonical bar normalization."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd

from apps.adapters.normalization import ProgressCallback, normalize_dukascopy_dataframe
from apps.dukascopy.data import (
    INTERVAL_DAY_1,
    INTERVAL_HOUR_1,
    INTERVAL_HOUR_4,
    INTERVAL_MIN_1,
    INTERVAL_MIN_15,
    INTERVAL_MIN_30,
    INTERVAL_MIN_5,
    OFFER_SIDE_BID,
    fetch as dukascopy_fetch,
)


class DukascopyHistoricalAdapter:
    """Fetch historical bars from Dukascopy and normalize to canonical schema."""

    _TIMEFRAME_TO_INTERVAL = {
        "M1": INTERVAL_MIN_1,
        "M5": INTERVAL_MIN_5,
        "M15": INTERVAL_MIN_15,
        "M30": INTERVAL_MIN_30,
        "H1": INTERVAL_HOUR_1,
        "H4": INTERVAL_HOUR_4,
        "D1": INTERVAL_DAY_1,
    }

    def __init__(
        self,
        fetcher: Optional[Callable[..., pd.DataFrame]] = None,
    ) -> None:
        self._fetcher = fetcher or dukascopy_fetch

    def fetch_historical(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> list[dict]:
        tf = timeframe.upper()
        interval = self._TIMEFRAME_TO_INTERVAL.get(tf)
        if interval is None:
            raise ValueError(f"Unsupported Dukascopy timeframe: {timeframe}")

        raw = self._fetcher(
            instrument=symbol,
            interval=interval,
            offer_side=OFFER_SIDE_BID,
            start=start,
            end=end,
        )
        if raw is None or raw.empty:
            return []

        return normalize_dukascopy_dataframe(
            raw,
            symbol=symbol,
            timeframe=tf,
            progress_callback=progress_callback,
        )

