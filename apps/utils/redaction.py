"""Secret redaction helpers for logs and API surfaces."""

from __future__ import annotations

import re
from typing import Any, Dict

REDACTED = "***REDACTED***"

SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "auth",
    "credential",
    "bearer",
    "smtp_password",
)

_JSON_PAIR_PATTERNS = [
    re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE),
    re.compile(r'("token"\s*:\s*")[^"]*(")', re.IGNORECASE),
    re.compile(r'("secret"\s*:\s*")[^"]*(")', re.IGNORECASE),
    re.compile(r'("api_key"\s*:\s*")[^"]*(")', re.IGNORECASE),
]

_KV_PATTERNS = [
    re.compile(r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|auth)\b\s*[:=]\s*([^\s,;]+)"),
]

_BEARER_PATTERN = re.compile(r"(?i)\b(Bearer)\s+([A-Za-z0-9\-._~+/=]+)")


def is_sensitive_key(key: str) -> bool:
    """Return True when a key likely contains a secret."""
    key_l = str(key).lower()
    return any(token in key_l for token in SENSITIVE_KEYWORDS)


def redact_scalar(value: Any) -> Any:
    """Redact scalar value while preserving type where possible."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return REDACTED
    return REDACTED


def redact_mapping(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact sensitive values in dictionaries."""
    out: Dict[str, Any] = {}
    for key, value in data.items():
        if is_sensitive_key(str(key)):
            out[key] = redact_scalar(value)
            continue

        if isinstance(value, dict):
            out[key] = redact_mapping(value)
        elif isinstance(value, list):
            out[key] = [
                redact_mapping(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def redact_text(text: str) -> str:
    """Redact common secret patterns from free-form text."""
    if not text:
        return text

    result = text

    for pattern in _JSON_PAIR_PATTERNS:
        result = pattern.sub(rf"\1{REDACTED}\2", result)

    for pattern in _KV_PATTERNS:
        result = pattern.sub(lambda m: f"{m.group(1)}={REDACTED}", result)

    result = _BEARER_PATTERN.sub(rf"\1 {REDACTED}", result)

    return result
