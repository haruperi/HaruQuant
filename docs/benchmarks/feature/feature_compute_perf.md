# Feature Pipeline Performance (IP-13)

Date: 2026-02-17

Configuration:
- Python feature pipeline: `apps/features/pipeline.py`
- Features: `sma(20), ema(20), rsi(14), atr(14), bbands(20,2.0), adl`
- Dataset: 1,000 synthetic 1-minute bars
- Machine: local dev environment

Results:
- batch compute total: `0.007595 s`
- streaming total (1,000 incremental updates): `6.573639 s`
- streaming average per bar: `6.573639 ms`

Notes:
- Streaming mode currently recomputes features on the buffered window for simplicity and determinism.
- This is acceptable for current IP-13 scope and can be optimized later with per-feature incremental kernels.
