# Data Ingestion and Normalization (IP-09)

## MT5 ZeroMQ (MQL5 EA stream)

- Adapter module: `apps/adapters/mt5_zmq_adapter.py`
- Normalizer module: `apps/adapters/normalization.py`
- Pipeline wrapper: `apps/adapters/pipeline.py`

Expected stream message envelope (JSON):

```json
{
  "provider": "mt5_ea",
  "schema_version": "1.0",
  "type": "tick",
  "symbol": "EURUSD",
  "event_time_utc": "2026-02-17T12:00:00Z",
  "sequence": 1,
  "source": "terminal-demo",
  "bid": 1.1010,
  "ask": 1.1012,
  "volume": 100.0
}
```

Minimal usage:

```python
from apps.adapters.mt5_zmq_adapter import MT5ZmqAdapter

adapter = MT5ZmqAdapter(
    endpoint="tcp://127.0.0.1:55781",
    topics=["tick.", "bar."],
    recv_timeout_ms=500,
)
adapter.start()
try:
    records = adapter.ingest(
        expected_count=10,
        progress_callback=lambda done, total, pct: print(done, total, pct),
    )
finally:
    adapter.stop()
```

Records returned from `ingest(...)` are canonical normalized dictionaries.

## Dukascopy Historical Adapter

- Adapter module: `apps/adapters/dukascopy_adapter.py`

Minimal usage:

```python
from datetime import datetime
from apps.adapters.dukascopy_adapter import DukascopyHistoricalAdapter

adapter = DukascopyHistoricalAdapter()
rows = adapter.fetch_historical(
    symbol="EURUSD",
    timeframe="M1",
    start=datetime(2026, 2, 1),
    end=datetime(2026, 2, 2),
    progress_callback=lambda done, total, pct: print(done, total, pct),
)
```

Each item in `rows` is a canonical bar payload.

## Unified Pipeline Helper

```python
from apps.adapters.pipeline import DataNormalizationPipeline

pipeline = DataNormalizationPipeline()
records = pipeline.ingest_mt5_stream(adapter, expected_count=100)
```

## Validation

- Contract checks:
  - `tests/contracts/test_tick_bar_contract.py`
- Real connection checks (localhost PUB/SUB):
  - `tests/integration/test_data_adapter_normalization.py`
