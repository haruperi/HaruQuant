# Zero-Copy and Fallback (IP-21)

This page shows bridge transfer modes for contiguous numeric payloads.

## Zero-copy direct path

```python
import numpy as np
import hqt_engine

arr = np.asarray([1.0, 2.0, 3.0], dtype=np.float64)
total = hqt_engine.sum_buffer_zero_copy(arr)
print(total)  # 6.0
```

## Auto path selection

```python
import hqt_engine

print(hqt_engine.sum_auto([1.0, 2.0, 3.0]))
# {"total": 6.0, "path": "copy_fallback"}
```

```python
import numpy as np
import hqt_engine

print(hqt_engine.sum_auto(np.asarray([1.0, 2.0, 3.0], dtype=np.float64)))
# {"total": 6.0, "path": "zero_copy"}
```

## Explicit serialization fallback

```python
from apps.utils.bridge_transfer import sum_with_fallback

print(sum_with_fallback([1.0, 2.0, 3.0], serialization="auto"))
print(sum_with_fallback([1.0, 2.0, 3.0], serialization="arrow"))     # requires pyarrow
print(sum_with_fallback([1.0, 2.0, 3.0], serialization="protobuf"))  # requires protobuf
```

## Capability query

```python
import hqt_engine
print(hqt_engine.bridge_transfer_capabilities())
```
