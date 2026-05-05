from __future__ import annotations

from haruquant.utils import REDACTED
from backend.agents import ContextRedactionMiddleware


def test_context_redaction_middleware_redacts_secrets_recursively() -> None:
    middleware = ContextRedactionMiddleware()

    redacted = middleware.redact(
        {
            "account": {
                "password": "super-secret",
                "headers": {"Authorization": "Bearer abc123"},
            },
            "notes": "token=abc123",
        }
    )

    assert redacted.payload["account"]["password"] == REDACTED
    assert redacted.payload["account"]["headers"]["Authorization"] == REDACTED
    assert redacted.payload["notes"] == "token=***REDACTED***"
    assert "account.password" in redacted.redacted_paths
    assert "account.headers.Authorization" in redacted.redacted_paths
    assert "notes" in redacted.redacted_paths


def test_context_redaction_middleware_redacts_privileged_state_keys() -> None:
    middleware = ContextRedactionMiddleware()

    redacted = middleware.redact(
        {
            "approval_token": "approval-secret",
            "risk_context": {"privileged_state": {"can_trade_live": True}},
        }
    )

    assert redacted.payload["approval_token"] == REDACTED
    assert redacted.payload["risk_context"]["privileged_state"] == REDACTED
    assert "approval_token" in redacted.redacted_paths
    assert "risk_context.privileged_state" in redacted.redacted_paths
