# Bridge Benchmark: Zero-Copy vs Fallback

Date: 2026-02-17
Environment: local Windows Release build (`build/bridge/Release/haruquant.pyd`)

## Micro-benchmark snippet

```python
import timeit
import numpy as np
import haruquant
from apps.utils.bridge_transfer import sum_with_fallback

arr = np.arange(8, dtype=np.float64)
listv = arr.tolist()

n = 200_000
print("sum_buffer_zero_copy_us", timeit.timeit("haruquant.sum_buffer_zero_copy(arr)", number=n, globals=globals()) / n * 1e6)
print("sum_auto_zero_copy_us", timeit.timeit("haruquant.sum_auto(arr)", number=n, globals=globals()) / n * 1e6)
print("sum_auto_copy_fallback_us", timeit.timeit("haruquant.sum_auto(listv)", number=n, globals=globals()) / n * 1e6)
```

## Observed results

- `sum_buffer_zero_copy_us`: `0.057862`
- `sum_auto_zero_copy_us`: `0.162200`
- `sum_auto_copy_fallback_us`: `0.192737`
- `arrow_fallback_us`: `156.112750` (serialization path, optional)
- `protobuf_fallback_us`: `n/a` in this environment (module not installed)

## Notes

- Zero-copy and auto-zero-copy paths are both below the `< 1μs` target in this benchmark.
- Arrow/Protobuf are explicit fallback transports for incompatible/cross-process style payloads, not low-latency hot-path replacements.
