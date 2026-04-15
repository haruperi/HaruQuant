"""Authentication and authorization helpers for the operator API."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.common.logger import logger

ALLOWED_OPERATOR_ROLES = {"operator", "approver", "admin"}
PUBLIC_PATH_PREFIXES = (
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
)


@dataclass(frozen=True)
class OperatorPrincipal:
    """Minimal operator identity extracted from request headers."""

    token: str
    actor_id: str
    role: str


def _is_public_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES) or path.startswith(
        "/api/operator/health"
    ) or path.startswith("/api/operator/events/stream")


def _extract_principal(request: Request) -> OperatorPrincipal:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = request.headers.get("X-HQ-Role", "operator").strip().lower()
    if role not in ALLOWED_OPERATOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unsupported operator role '{role}'.",
        )

    actor_id = request.headers.get("X-HQ-Actor-Id", "operator:anonymous").strip()
    return OperatorPrincipal(token=token, actor_id=actor_id, role=role)


class OperatorAuthMiddleware(BaseHTTPMiddleware):
    """Attach a minimal operator principal to protected operator API requests."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if not request.url.path.startswith("/api/operator") or _is_public_path(request.url.path):
            return await call_next(request)

        try:
            request.state.operator_principal = _extract_principal(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )

        return await call_next(request)


def get_operator_principal(request: Request) -> OperatorPrincipal:
    """Return the authenticated operator principal for a request."""

    principal = getattr(request.state, "operator_principal", None)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operator principal is not available.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_operator_role(request: Request, *allowed_roles: str) -> OperatorPrincipal:
    """Enforce that the current operator has one of the allowed roles."""

    principal = get_operator_principal(request)
    if allowed_roles and principal.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role is not authorized for this action.",
        )
    return principal
