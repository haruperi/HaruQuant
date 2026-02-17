# Multi-Symbol Ingestion (IP-11)

## Scope

Implemented in:
- `apps/adapters/multisymbol_ingestion.py`

Capabilities:
- synchronized multi-symbol timelines
- incremental compaction (merge + dedupe by timestamp)
- mmap lazy loading for historical arrays

## Synchronize Multiple Symbols

```python
from apps.adapters.multisymbol_ingestion import MultiSymbolIngestionPipeline

pipeline = MultiSymbolIngestionPipeline()
synced, summary = pipeline.synchronize(
    data_by_symbol={"EURUSD": eurusd_df, "GBPUSD": gbpusd_df},
    method="ffill",
)
print(summary.common_rows)
```

## Compact Incremental Downloads

```python
compacted = pipeline.compact_incremental(existing_df, incoming_df)
```

Compaction policy:
- append existing + incoming
- sort by datetime index
- keep latest row for duplicate timestamps

## Memory-Mapped Lazy Loading

```python
import numpy as np
from apps.adapters.multisymbol_ingestion import MemmapHistoricalStore

store = MemmapHistoricalStore("artifacts/evidence/mmap_store")
store.write_array("EURUSD", np.random.rand(1000, 5))
mm = store.read_memmap("EURUSD")  # numpy.memmap, lazy read
print(mm.shape)
```

## Real MT5 Data Example

For a live multi-symbol ingestion example using real MT5 bars, run:

```bash
python tests/usage/utils/usage_multisymbol_ingestion_mt5.py
```

This script:
- loads MT5 credentials via `UserManager`
- fetches bars for `EURUSD`, `GBPUSD`, and `USDJPY`
- synchronizes all symbols to a common timeline with `method="ffill"`
- prints before/after row counts and common synchronized rows

Example output (shape may vary by broker/history):

```text
IP-11 REAL MT5 MULTI-SYMBOL INGESTION EXAMPLE
EURUSD: fetched 672 bars
GBPUSD: fetched 670 bars
USDJPY: fetched 672 bars
---- Synchronization summary ----
symbols: 3
rows_before: {'EURUSD': 672, 'GBPUSD': 670, 'USDJPY': 672}
rows_after: {'EURUSD': 668, 'GBPUSD': 668, 'USDJPY': 668}
common_rows: 668
```
