# IP-11 Multi-Symbol Synchronization Performance Snapshot

Date: 2026-02-17
Environment: local developer machine (Python)

## Benchmarks (Synthetic)

- Synchronization (`MultiSymbolIngestionPipeline.synchronize`)
  - symbols: `3`
  - timeline rows (common): `19,998`
  - elapsed: `0.009276s`
  - throughput: `2,155,979 rows/s`

- Incremental compaction (`compact_incremental`)
  - output rows: `20,000`
  - elapsed: `0.001941s`
  - throughput: `10,305,028 rows/s`

- mmap lazy loading (`MemmapHistoricalStore`)
  - array shape: `(50,000, 8)`
  - write+open+single read elapsed: `0.003889s`

## Notes

- These are synthetic local benchmarks for ingestion primitives.
- Functional validation is covered in:
  - `tests/integration/test_multisymbol_sync.py`
