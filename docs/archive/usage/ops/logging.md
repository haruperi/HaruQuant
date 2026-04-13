# Logging Operations Guide

This document describes how to operate and validate HaruQuant logging features in production and development.

## Stack Overview

- Python logging adapter: `apps/utils/logger.py` (`structlog`-backed)
- C++ logging backend: `cpp/src/engine/logger.cpp` (`spdlog` async)
- Bridge module: `haruquant` (Python <-> C++ logging controls)

## Severity Normalization (C++ + Python)

Canonical severity levels:

- `DEBUG` (10)
- `INFO` (20)
- `WARNING` (30)
- `ERROR` (40)
- `CRITICAL` (50)

Accepted aliases:

- `warn` -> `WARNING`
- `fatal` -> `CRITICAL`

Python usage:

```python
from backend.common.logger import logger

logger.log("warn", "warning example")
logger.log("fatal", "critical example")
```

C++ bridge usage:

```python
import haruquant

haruquant.set_log_level("warn")
haruquant.emit_log("fatal", "critical event")
```

## Correlation IDs in Schema

All records carry these schema fields:

- `correlation_id`
- `run_id`
- `trace_id`

Python usage:

```python
from backend.common.logger import logger

log = logger.bind(
    correlation_id="corr-001",
    run_id="run-20260217",
    trace_id="trace-abc",
)
log.info("order submitted")
```

C++ bridge callback records expose the same keys in payload.

## Dynamic Runtime Filtering (FR-UTIL-006)

### Python adapter controls

```python
from backend.common.logger import logger

logger.set_min_level("INFO")
logger.set_component_level("risk", "ERROR")

logger.info("risk info filtered", component="risk")
logger.error("risk error emitted", component="risk")

logger.clear_component_level("risk")
logger.clear_all_component_levels()
logger.set_min_level("TRACE")
```

### C++ bridge controls

```python
import haruquant

haruquant.set_log_level("debug")
haruquant.set_component_log_level("module", "error")

haruquant.emit_log("info", "filtered for module")
haruquant.emit_log("error", "emitted for module")

haruquant.clear_component_log_level("module")
haruquant.clear_all_component_log_levels()
```

## Sensitive Data Redaction (FR-UTIL-008)

Redaction is automatic in both Python and C++ logger paths.

Sensitive key/value fields and message patterns are masked before sink/callback dispatch.

Examples that are redacted:

- `password=...`
- `token=...`
- `api_key=...`
- `Bearer ...`
- sensitive keys in structured metadata (for example `password`, `api_key`, `secret`, `smtp_password`)

Redacted token:

- `***REDACTED***`

Python example:

```python
from backend.common.logger import logger

logger.error(
    "auth failed password=supersecret token=abcd",
    extra={"api_key": "never-log-this", "safe": "ok"},
)
```

## Operator Validation Scripts

Run these scripts to verify behavior end-to-end:

```bash
python tests/usage/logger/09_structlog_adapter_usage.py
python tests/usage/logger/10_unified_logging_features.py
python tests/usage/logger/11_cpp_spdlog_bridge_usage.py
```

Additional adapter behavior examples:

```bash
python tests/usage/logger/01_basic_usage.py
python tests/usage/logger/03_handlers.py
python tests/usage/logger/04_context_binding.py
python tests/usage/logger/06_file_sink_compatibility_options.py
python tests/usage/logger/07_raw_record_capture.py
```

## Notes

- In mixed environments, bridge capabilities can differ if an older `haruquant` binary is loaded.
- The usage scripts are written to degrade gracefully when optional bridge APIs are unavailable.
- Keep stderr logging disabled during callback-based tests to reduce noisy output:

```python
haruquant.set_stderr_logging(False)
```
