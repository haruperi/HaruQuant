"""Firm-facing execution facade.

Business logic remains in `services.execution`, `services.execution.live`,
and governed MCP broker wrappers during the Phase 2 additive migration.

The package initializer is intentionally import-light so importing a specific
submodule, such as `backend_retiring.execution.ctrader_bridge`, does not eagerly load
broker integrations.
"""

__all__ = []
