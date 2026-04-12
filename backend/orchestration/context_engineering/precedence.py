"""Source-of-truth precedence (Playbook §9.4)."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Dict, List, Optional


class TrustLevel(IntEnum):
    """Trust hierarchy for context sources (Playbook §9.4)."""
    SYSTEM_POLICY = 0
    WORKFLOW_POLICY = 1
    SESSION_STATE = 2
    APPROVED_USER_INPUT = 3
    TRUSTED_RESOURCES = 4
    RETRIEVED_DOCUMENTS = 5
    RAW_TOOL_OUTPUT = 6


class SourcePrecedence:
    """Resolve conflicts based on source trust level."""

    def __init__(self) -> None:
        self._overrides: Dict[str, TrustLevel] = {}

    def resolve(
        self, key: str, sources: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Return the value from the most trusted source."""
        if not sources:
            return None

        def trust_score(src: Dict[str, Any]) -> int:
            src_type = src.get("source_type", "unknown").upper()
            # Map to enum if it matches, else override or default
            if src_type in self._overrides:
                return int(self._overrides[src_type])
            # Try to map to TrustLevel by name
            for lvl in TrustLevel:
                if src_type == lvl.name or src_type.lower() == lvl.name.lower():
                    return int(lvl)
            return int(TrustLevel.RAW_TOOL_OUTPUT)

        return min(sources, key=trust_score)

    def set_override(self, source_type: str, level: TrustLevel) -> None:
        self._Overrides[source_type] = level

    @property
    def hierarchy(self) -> List[str]:
        return [lvl.name for lvl in TrustLevel]
