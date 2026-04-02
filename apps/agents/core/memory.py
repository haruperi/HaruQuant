"""Short-lived run memory for workflow-scoped intermediate values."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RunMemory:
    """Simple in-memory store for one workflow run."""

    values: Dict[str, Any] = field(default_factory=dict)

    def put(self, key: str, value: Any) -> None:
        """Store one workflow-local value."""
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Read one workflow-local value."""
        return self.values.get(key, default)
