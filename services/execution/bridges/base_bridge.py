"""Base interface for broker execution bridges."""
from datetime import datetime, timezone
from typing import Any
class BaseExecutionBridge:
    bridge_name = "base"
    def __init__(self, *, live_enabled: bool = False) -> None:
        self.live_enabled = live_enabled
        self.connected = True
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
    def heartbeat(self) -> dict[str, Any]:
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        return {"bridge": self.bridge_name, "status": "healthy" if self.connected else "disconnected", "last_heartbeat": self.last_heartbeat}
    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if not self.live_enabled:
            return {"bridge": self.bridge_name, "status": "blocked", "reason": "live_execution_disabled", "order": order}
        return {"bridge": self.bridge_name, "status": "accepted", "order": order}
