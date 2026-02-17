"""Integration tests for multi-symbol synchronized ingestion (IP-11)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from apps.adapters.multisymbol_ingestion import MemmapHistoricalStore, MultiSymbolIngestionPipeline


def test_multisymbol_synchronize_pipeline_ffill():
    idx_a = pd.date_range("2026-02-17 00:00:00", periods=5, freq="h")
    idx_b = idx_a.delete([1, 3])

    a = pd.DataFrame({"close": [1.1, 1.2, 1.3, 1.4, 1.5]}, index=idx_a)
    b = pd.DataFrame({"close": [2.1, 2.3, 2.5]}, index=idx_b)

    synced, summary = MultiSymbolIngestionPipeline.synchronize(
        {"EURUSD": a, "GBPUSD": b},
        method="ffill",
    )

    assert set(synced.keys()) == {"EURUSD", "GBPUSD"}
    assert len(synced["EURUSD"]) == len(synced["GBPUSD"])
    assert summary.symbols == 2
    assert summary.common_rows == len(synced["EURUSD"])
    assert not synced["GBPUSD"].isna().any().any()


def test_compact_incremental_merges_and_deduplicates_keep_last():
    idx_existing = pd.to_datetime(["2026-02-17 00:00:00", "2026-02-17 01:00:00"])
    idx_incoming = pd.to_datetime(["2026-02-17 01:00:00", "2026-02-17 02:00:00"])

    existing = pd.DataFrame({"close": [1.1, 1.2]}, index=idx_existing)
    incoming = pd.DataFrame({"close": [1.25, 1.3]}, index=idx_incoming)

    out = MultiSymbolIngestionPipeline.compact_incremental(existing, incoming)
    assert list(out.index) == list(pd.to_datetime(["2026-02-17 00:00:00", "2026-02-17 01:00:00", "2026-02-17 02:00:00"]))
    assert out.loc[pd.Timestamp("2026-02-17 01:00:00"), "close"] == 1.25


def test_memmap_historical_store_lazy_loading():
    root = Path(".tmp_ip11_memmap")
    root.mkdir(parents=True, exist_ok=True)
    store = MemmapHistoricalStore(root / "mmap_store")
    data = np.arange(100, dtype=np.float64).reshape(20, 5)
    store.write_array("EURUSD", data)

    mm = store.read_memmap("EURUSD")
    assert isinstance(mm, np.memmap)
    assert mm.shape == (20, 5)
    assert float(mm[0, 0]) == 0.0
    assert float(mm[-1, -1]) == 99.0
