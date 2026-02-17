# HaruQuant Architecture Notes

## C++ Logging Backend

- C++ logging API remains `hqt::util` (`cpp/include/util/logger.hpp`) to keep bridge and Python integrations stable.
- Backend implementation uses `spdlog` async logger in `cpp/src/engine/logger.cpp`.
- Logging path:
  - Structured `LogRecord` is built in-process for callback forwarding (`set_log_sink`).
  - Stderr emission is handled asynchronously via `spdlog::async_logger` to avoid blocking hot paths.
- Runtime controls:
  - `set_log_level(...)` updates filtering level.
  - `set_component_log_level(component, level)` overrides filtering for one component.
  - `clear_component_log_level(component)` removes one component override.
  - `clear_all_component_log_levels()` resets all component overrides.
  - `set_stderr_logging(...)` toggles async stderr output.
  - `set_log_sink(...)` controls structured callback forwarding.

## Python Logging Adapter

- Default Python logger export is `apps.utils.logger.logger` (Structlog adapter).
- Existing import pattern `from apps.utils.logger import logger` remains unchanged.
- Compatibility support is preserved for commonly used APIs:
  - level methods (`debug/info/success/warning/error/critical/exception`)
  - `bind(...)`
  - `add(...)` / `remove(...)` sink management for runtime callbacks (including raw callback mode)
- Sensitive fields and free-form text are redacted before dispatch using `apps/utils/redaction.py`.
- If `structlog` is unavailable in the environment, adapter falls back to stdlib logging while preserving the same call interface.

## Log Schema IDs

- Normalized identifier fields included in log schema:
  - `correlation_id`
  - `run_id`
  - `trace_id`

- Behavior:
  - Python adapter (`apps.utils.logger`) injects these keys into every record `extra` payload.
  - C++ logger (`hqt::util::LogRecord`) includes these fields explicitly and mirrors them in bridge callback payloads.
  - If not provided by caller context, values default to empty strings to keep schema stable.

## Severity Contract (Normalized)

- Canonical severity levels across C++ and Python:
  - `DEBUG` (10)
  - `INFO` (20)
  - `WARNING` (30)
  - `ERROR` (40)
  - `CRITICAL` (50)

- Accepted aliases (normalized to canonical):
  - `warn` -> `WARNING`
  - `fatal` -> `CRITICAL`

- C++ bridge input (`hqt_engine.set_log_level`, `hqt_engine.emit_log`) accepts:
  - `debug`, `info`, `warning|warn`, `error`, `critical|fatal`

- Python adapter (`apps.utils.logger`) accepts:
  - canonical names above plus aliases `WARN`, `FATAL`

## Runtime Filtering (FR-UTIL-006)

- Runtime filtering is supported in both C++ and Python by:
  - global minimum severity threshold
  - per-component severity overrides
- Component resolution order:
  - `extra["component"]` if present
  - logger/module name fallback
- Bridge controls exposed via `hqt_engine`:
  - `set_log_level(level)`
  - `set_component_log_level(component, level)`
  - `clear_component_log_level(component)`
  - `clear_all_component_log_levels()`
- Python adapter controls (`apps.utils.logger.StructlogAdapter`):
  - `set_min_level(level)` / `get_min_level()`
  - `set_component_level(component, level)`
  - `clear_component_level(component)`
  - `clear_all_component_levels()`

## Sensitive Data Redaction (FR-UTIL-008)

- Redaction is automatic in both logger stacks:
  - Python: `apps/utils/redaction.py` + `apps/utils/logger.py`
  - C++: `cpp/src/engine/logger.cpp`
- Redaction behavior:
  - sensitive key/value fields in structured metadata are replaced with `***REDACTED***`
  - free-form message patterns such as `password=...`, `token=...`, `api_key=...`, and `Bearer ...` are redacted
- Redaction happens before sink/callback dispatch and before stderr output to prevent accidental secret leakage in downstream handlers.

