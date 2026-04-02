"""Append-only audit logging for agent workflow runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AgentAuditEvent:
    """One append-only agent audit entry."""

    event_type: str
    task_id: str
    run_id: str
    workflow_name: str
    correlation_id: str
    status: str
    user_id: int
    actor_role: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    approval_event: Optional[Dict[str, Any]] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


class AgentAuditLogger:
    """Small JSONL audit sink for workflow runs."""

    def __init__(self, audit_log_path: str | Path) -> None:
        self.audit_log_path = Path(audit_log_path)

    def append(self, event: AgentAuditEvent) -> None:
        """Append one immutable audit event."""
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True))
            handle.write("\n")
