# IP-09 Ingestion Throughput Snapshot

Date: 2026-02-17
Environment: local developer machine (Python)

## Canonical Normalization Throughput (Synthetic)

- Dukascopy bar normalization (`normalize_dukascopy_dataframe`, 10,000 rows):
  - elapsed: `0.251533s`
  - throughput: `39,756 rows/s`
- MT5 event normalization (`normalize_mt5_event`, 10,000 events):
  - elapsed: `0.037222s`
  - throughput: `268,656 events/s`

## Notes

- This benchmark measures normalization stage only (not network I/O).
- Real MT5 ZMQ socket connectivity is covered in:
  - `tests/integration/test_data_adapter_normalization.py`
