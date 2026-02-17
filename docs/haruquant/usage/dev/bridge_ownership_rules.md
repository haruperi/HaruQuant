# Bridge Ownership Rules (IP-19)

## Scope

Defines explicit C++/Python ownership contracts for nanobind bridge objects.

Primary API:
- `hqt_engine.ownership_contracts()`

## Ownership Modes

- `cpp_owned_python_view`
  - C++ owns object lifetime.
  - Python receives non-owning views/references.
- `shared_ownership`
  - Long-lived bridge objects are exposed with shared pointer holders.
- `python_callback_owner`
  - Python owns callback objects; C++ keeps callable handles and clears on teardown.
- `buffer_view_zero_copy`
  - Heavy numeric payloads can be ingested through Python buffer protocol without copy.

## Quick Usage

```python
import hqt_engine
import numpy as np

print(hqt_engine.ownership_contracts())

arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
print(hqt_engine.sum_buffer_zero_copy(arr))  # zero-copy buffer view path
```
