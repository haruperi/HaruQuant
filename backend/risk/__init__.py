"""Firm-facing deterministic risk facade.

Business logic remains in `backend.services.risk`, `backend.services.risk_engine`,
and `backend.services.safety` during the Phase 2 additive migration.

The package initializer is intentionally import-light. Import the specific
facade submodule needed by a caller.
"""

__all__ = []
