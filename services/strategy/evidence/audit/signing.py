"""Signed audit evidence helpers."""

from __future__ import annotations

import hashlib
import hmac

from backend_retiring.contracts.serialization import canonical_json_dumps


def sign_audit_evidence(
    payload: dict[str, object],
    *,
    secret_key: str,
) -> dict[str, str]:
    """Emit a stable HMAC signature for audit evidence payloads."""

    message = canonical_json_dumps(payload).encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return {
        "algorithm": "hmac-sha256",
        "signature": signature,
    }


def verify_audit_signature(
    payload: dict[str, object],
    *,
    secret_key: str,
    signature: str,
) -> bool:
    """Verify an emitted audit evidence signature."""

    expected = sign_audit_evidence(payload, secret_key=secret_key)["signature"]
    return hmac.compare_digest(expected, signature)
