"""Shared service-to-service authorization for MCP calls."""

from __future__ import annotations

from dataclasses import dataclass


class MCPServiceAuthError(PermissionError):
    """Raised when a service-to-service MCP call is unauthorized."""


@dataclass(frozen=True)
class MCPServicePrincipal:
    """Minimal authenticated MCP caller identity."""

    service_id: str


@dataclass(frozen=True)
class MCPServiceAuthorizer:
    """Authorize internal MCP callers by shared secret and explicit service allowlist."""

    shared_secret: str
    allowed_service_ids: tuple[str, ...]

    def authorize(self, *, service_id: str, bearer_token: str) -> MCPServicePrincipal:
        if bearer_token != self.shared_secret:
            raise MCPServiceAuthError("invalid service token")
        if service_id not in self.allowed_service_ids:
            raise MCPServiceAuthError(f"service '{service_id}' is not authorized for MCP access")
        return MCPServicePrincipal(service_id=service_id)
