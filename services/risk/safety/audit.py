"""Kill-switch event persistence and audit helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data.database import GovernanceRepository, KillSwitchEventRecord
from services.governance.workflow import KillSwitchState


class KillSwitchAuditService:
    """Append-only audit logging for kill-switch state changes."""

    def __init__(self, db_path: str | Path) -> None:
        self.repository = GovernanceRepository(db_path)

    def log_event(
        self,
        *,
        previous_state: KillSwitchState,
        new_state: KillSwitchState,
        trigger_type: str,
        reason_code: str,
        actor_type: str,
        actor_id: str,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KillSwitchEventRecord:
        return self.repository.create_kill_switch_event(
            previous_state=previous_state.value,
            new_state=new_state.value,
            trigger_type=trigger_type,
            reason_code=reason_code,
            actor_type=actor_type,
            actor_id=actor_id,
            workflow_id=workflow_id,
            metadata_json=json.dumps(metadata or {}, sort_keys=True, separators=(",", ":")),
        )


__all__ = ["KillSwitchAuditService"]
