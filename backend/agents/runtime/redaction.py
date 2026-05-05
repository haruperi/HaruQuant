"""Context redaction middleware for model-facing runtime payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.utils.logger import logger
from services.utils.redaction import REDACTED, is_sensitive_key, redact_mapping, redact_text


_DEFAULT_PRIVILEGED_KEYS: tuple[str, ...] = (
    "approval_token",
    "override_request",
    "override_decision",
    "kill_switch_recovery",
    "privileged_state",
)


@dataclass(frozen=True)
class RedactedContext:
    payload: dict[str, Any]
    redacted_paths: tuple[str, ...]


class ContextRedactionMiddleware:
    """Redact secrets and explicitly privileged context before agent execution."""

    def __init__(
        self,
        *,
        privileged_keys: tuple[str, ...] = _DEFAULT_PRIVILEGED_KEYS,
    ) -> None:
        self._privileged_keys = tuple(key.lower() for key in privileged_keys)

    def redact(self, payload: dict[str, Any]) -> RedactedContext:
        redacted_paths: list[str] = []

        def _redact_value(value: Any, *, path: str) -> Any:
            if isinstance(value, dict):
                safe_mapping = redact_mapping(value)
                redacted_mapping: dict[str, Any] = {}
                for key, nested_value in safe_mapping.items():
                    key_path = f"{path}.{key}" if path else str(key)
                    if self._is_privileged_key(str(key)):
                        redacted_paths.append(key_path)
                        redacted_mapping[key] = REDACTED
                    else:
                        redacted_mapping[key] = _redact_value(nested_value, path=key_path)
                return redacted_mapping
            if isinstance(value, list):
                return [
                    _redact_value(item, path=f"{path}[{index}]")
                    for index, item in enumerate(value)
                ]
            if isinstance(value, str):
                redacted_text = redact_text(value)
                if redacted_text != value:
                    redacted_paths.append(path)
                return redacted_text
            return value

        redacted_payload = _redact_value(payload, path="")
        return RedactedContext(
            payload=redacted_payload,
            redacted_paths=tuple(dict.fromkeys(path for path in redacted_paths if path)),
        )

    def _is_privileged_key(self, key: str) -> bool:
        normalized = key.lower()
        return normalized in self._privileged_keys or is_sensitive_key(normalized)
