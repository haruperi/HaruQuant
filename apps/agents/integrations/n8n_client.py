"""Local-safe outbound workflow stub for future n8n integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class N8NClient:
    """Very small local-first client for outbound workflow triggers."""

    def __init__(self, outbound_dir: str | Path = "artifacts/workflows/n8n_outbox") -> None:
        self.outbound_dir = Path(outbound_dir)

    def trigger_workflow(self, *, workflow_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Persist an outbound workflow payload locally for later delivery."""
        self.outbound_dir.mkdir(parents=True, exist_ok=True)
        path = self.outbound_dir / f"{workflow_name}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return {
            "status": "queued_local",
            "workflow_name": workflow_name,
            "artifact_ref": str(path),
        }
