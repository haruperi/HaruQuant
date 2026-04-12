"""Redaction rules implementation (Playbook §16.4)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set


class RedactionRules:
    """Field-level redaction for secrets, PII, and credentials."""

    SENSITIVE_PATTERNS = [
        re.compile(r"password", re.IGNORECASE),
        re.compile(r"secret", re.IGNORECASE),
        re.compile(r"token", re.IGNORECASE),
        re.compile(r"api.?key", re.IGNORECASE),
        re.compile(r"auth", re.IGNORECASE),
        re.compile(r"credential", re.IGNORECASE),
    ]

    REDACTED_VALUE = "[REDACTED]"

    def __init__(
        self,
        sensitive_fields: Optional[Set[str]] = None,
        sensitive_patterns: Optional[List[str]] = None,
    ) -> None:
        self._sensitive_fields = sensitive_fields or set()
        self._extra_patterns = [
            re.compile(p, re.IGNORECASE) for p in (sensitive_patterns or [])
        ]

    def redact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of data with sensitive fields redacted."""
        result = {}
        for key, value in data.items():
            if self._is_sensitive(key):
                result[key] = self.REDACTED_VALUE
            elif isinstance(value, dict):
                result[key] = self.redact(value)
            else:
                result[key] = value
        return result

    def _is_sensitive(self, field: str) -> bool:
        if field.lower() in {f.lower() for f in self._sensitive_fields}:
            return True
        for pattern in self.SENSITIVE_PATTERNS + self._extra_patterns:
            if pattern.search(field):
                return True
        return False

    def add_sensitive_field(self, field: str) -> None:
        self._sensitive_fields.add(field)
