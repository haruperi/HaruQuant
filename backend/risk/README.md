# Risk Facade

Firm-facing risk package for Phase 2.

This package intentionally wraps existing deterministic risk services instead of duplicating them. The source of truth remains in:

- `backend/services/risk/`
- `backend/services/risk_engine/`
- `backend/services/safety/`
- `backend/services/approval/`

Agents may use this package as a stable import surface, but RiskGovernor decisions remain deterministic and binding.
