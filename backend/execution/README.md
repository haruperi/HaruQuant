# Execution Facade

Firm-facing execution package for Phase 2.

This package wraps the existing governed execution path rather than creating a second execution system. The source of truth remains in:

- `services/execution/`
- `services/execution/live/`
- `backend/mcp/mt5_mcp/`
- `services/execution/shadow/`
- `services/simulation/`

Live orders must still pass RiskGovernor, kill switch, approval, pre-send validation, broker boundary, receipt persistence, reconciliation, and audit logging.
