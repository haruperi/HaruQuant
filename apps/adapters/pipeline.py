"""Unified data-source normalization pipeline helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from apps.adapters.dukascopy_adapter import DukascopyHistoricalAdapter
from apps.adapters.mt5_zmq_adapter import MT5ZmqAdapter, ProgressCallback


class DataNormalizationPipeline:
    """Simple orchestration wrapper for adapter ingestion and normalization."""

    def ingest_mt5_stream(
        self,
        adapter: MT5ZmqAdapter,
        expected_count: int,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> list[dict]:
        return adapter.ingest(expected_count=expected_count, progress_callback=progress_callback)

    def ingest_dukascopy_historical(
        self,
        adapter: DukascopyHistoricalAdapter,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> list[dict]:
        return adapter.fetch_historical(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            progress_callback=progress_callback,
        )

