# Execution Facade

Firm-facing execution package for Phase 2.

This package wraps the existing governed execution path rather than creating a second execution system. The source of truth remains in:

- `backend/services/execution/`
- `backend/services/live_trading/`
- `backend/mcp/mt5_mcp/`
- `backend/services/shadow/`
- `backend/services/simulation/`

Live orders must still pass RiskGovernor, kill switch, approval, pre-send validation, broker boundary, receipt persistence, reconciliation, and audit logging.
