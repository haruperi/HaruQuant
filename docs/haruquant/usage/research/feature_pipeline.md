# Feature Pipeline (IP-13)

## Scope

Implemented in:
- `backend/services/features/pipeline.py`

Provides:
- versioned feature pipeline metadata
- deterministic feature pipeline fingerprint metadata
- batch feature computation over historical bars
- incremental (streaming) feature computation with per-symbol buffers
- inspectable feature dependency graph

## Supported Features

- `sma`
- `ema`
- `wma`
- `rsi`
- `atr`
- `bbands`
- `adl` (`accumulation_distribution`)

## Usage

Run:

```bash
python tests/usage/utils/usage_feature_pipeline.py
```

The usage script demonstrates:
- batch compute
- incremental streaming updates
- graph inspection (`nodes` + `edges`)
