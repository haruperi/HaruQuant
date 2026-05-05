# Security

Status: canonical security spec
Scope: identity, authorization, secrets, and least-privilege controls
Use this when: you need security boundaries and enforcement expectations
Companion docs: `Requirements.md`, `System_Architecture.md`, `Observability_Audit.md`
Owner: security and platform
Review cadence: quarterly or when security controls change

## Identity Model
- User identity: JWT-based authentication via `backend_retiring/api/auth_utils.py`
- Service identity: API key or mTLS for inter-service communication
- Agent identity: Named agent with role-based permissions

## Authn/Authz Boundaries
- API gateway: Bearer token authentication for all routes
- MCP servers: Allowlist-based caller validation via `metadata.yaml`
- Internal services: Trust boundary at process boundary

## Secret Management
- Secrets stored in environment variables or system keyring
- Never logged or stored in code/config files
- Redaction via `backend_retiring/observability/redaction.py`

## Least Privilege Model
- Read-only MCP servers cannot execute mutating tools
- Execution requires approval packet (Playbook Â§11)
- Kill switch can revoke all execution permissions instantly

## Network Boundaries
- Internal: All backend services communicate via Python imports (no network)
- External: MT5 terminal (local), Dukascopy (HTTPS), notification APIs (HTTPS)

## Code Execution Restrictions
- No arbitrary code execution from user input
- Strategy code loaded from file system with validation
- MCP tools use typed parameters only

## Sandboxing Requirements
- Simulation engine runs in-process with no MT5 access
- Live trading restricted to approved symbols and position sizes
- Risk gates block execution before any side effect

## Retention and Deletion Rules
- Audit logs retained per `retention_policy.yaml`
- Personal data redacted before logging
- Legal hold overrides all retention rules

