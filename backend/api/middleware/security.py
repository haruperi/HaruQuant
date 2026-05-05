"""API middleware for secret-safe request logging."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from services.utils.logger import logger
from services.utils.redaction import redact_mapping


class SecretRedactionMiddleware(BaseHTTPMiddleware):
    """Sanitize request metadata before it is written to logs."""

    async def dispatch(self, request: Request, call_next):
        safe_headers: Dict[str, Any] = redact_mapping(dict(request.headers))
        safe_query: Dict[str, Any] = redact_mapping(dict(request.query_params))

        logger.debug(
            "HTTP request {method} {path}",
            method=request.method,
            path=request.url.path,
            extra={
                "http": {
                    "method": request.method,
                    "path": request.url.path,
                    "headers": safe_headers,
                    "query": safe_query,
                }
            },
        )

        response = await call_next(request)
        return response

