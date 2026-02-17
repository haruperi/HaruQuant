"""Multi-symbol synchronized ingestion utilities (IP-11)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Mapping, Optional

import numpy as np
import pandas as pd

from apps.simulation.synchronizer import DataSynchronizer
from apps.utils.path_utils import ensure_dir


SyncMethod = Literal["ffill", "drop", "interpolate"]


@dataclass
class SyncSummary:
    """Basic synchronization summary."""

    symbols: int
    rows_before: Dict[str, int]
    rows_after: Dict[str, int]
    common_rows: int


class MultiSymbolIngestionPipeline:
    """Thin orchestration wrapper for synchronized multi-symbol ingestion."""

    @staticmethod
    def synchronize(
        data_by_symbol: Mapping[str, pd.DataFrame],
        method: SyncMethod = "ffill",
        handle_leading_nans: Literal["drop", "fill"] = "drop",
        handle_trailing_nans: Literal["drop", "fill"] = "drop",
    ) -> tuple[Dict[str, pd.DataFrame], SyncSummary]:
        rows_before = {symbol: len(df) for symbol, df in data_by_symbol.items()}
        synced = DataSynchronizer.synchronize(
            dict(data_by_symbol),
            method=method,
            handle_leading_nans=handle_leading_nans,
            handle_trailing_nans=handle_trailing_nans,
        )
        rows_after = {symbol: len(df) for symbol, df in synced.items()}
        common_rows = min(rows_after.values()) if rows_after else 0
        return synced, SyncSummary(
            symbols=len(synced),
            rows_before=rows_before,
            rows_after=rows_after,
            common_rows=common_rows,
        )

    @staticmethod
    def compact_incremental(
        existing: Optional[pd.DataFrame],
        incoming: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Merge incremental data into existing dataset.

        Policy:
        - concatenate existing + incoming
        - sort by index
        - keep last row for duplicate timestamps
        """
        if existing is None or existing.empty:
            out = incoming.copy()
        else:
            out = pd.concat([existing, incoming], axis=0)
        if not isinstance(out.index, pd.DatetimeIndex):
            raise ValueError("compact_incremental requires DatetimeIndex")
        out = out.sort_index()
        out = out[~out.index.duplicated(keep="last")]
        return out


class MemmapHistoricalStore:
    """Simple memory-mapped historical store for lazy symbol data access."""

    def __init__(self, base_dir: Path | str):
        self.base_dir = ensure_dir(base_dir)

    def symbol_path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_")
        return self.base_dir / f"{safe}.npy"

    def write_array(self, symbol: str, values: np.ndarray) -> Path:
        path = self.symbol_path(symbol)
        np.save(path, values)
        return path

    def read_memmap(self, symbol: str) -> np.memmap:
        path = self.symbol_path(symbol)
        if not path.exists():
            raise FileNotFoundError(path)
        arr = np.load(path, mmap_mode="r")
        if not isinstance(arr, np.memmap):
            # np.load with mmap_mode should return memmap, but keep explicit.
            arr = np.memmap(path, mode="r")
        return arr

