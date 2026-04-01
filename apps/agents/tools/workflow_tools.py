"""Advisory workflow notification and outbound trigger helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from apps.agents.integrations.n8n_client import N8NClient
from apps.notifications.base import NotificationLevel, NotificationMessage
from apps.notifications.manager import NotificationManager


class WorkflowTools:
    """Send notifications or enqueue outbound workflow payloads safely."""

    def __init__(
        self,
        *,
        notification_manager: Optional[NotificationManager] = None,
        n8n_client: Optional[N8NClient] = None,
    ) -> None:
        self.notification_manager = notification_manager or NotificationManager()
        self.n8n_client = n8n_client or N8NClient()

    def workflow_send_notification(
        self,
        *,
        title: str,
        body: str,
        level: str = "INFO",
        services: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a safe operator notification through configured channels."""
        message = NotificationMessage(
            title=title,
            body=body,
            level=NotificationLevel(level),
            metadata=dict(metadata or {}),
        )
        results = self.notification_manager.send_notification(message, services=services)
        return {
            "message": {"title": title, "level": level, "metadata": dict(metadata or {})},
            "services_requested": services or list(self.notification_manager.notifiers.keys()),
            "results": {name: asdict(result) for name, result in results.items()},
        }

    def workflow_trigger_n8n(
        self,
        *,
        workflow_name: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Queue one outbound workflow payload for future integration delivery."""
        return self.n8n_client.trigger_workflow(workflow_name=workflow_name, payload=payload)
