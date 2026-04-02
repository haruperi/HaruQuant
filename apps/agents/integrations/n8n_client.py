"""Outbound n8n integration client with signed-webhook and local fallback modes."""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import request

from apps.agents.core.policies import N8NSettings
from apps.agents.integrations.n8n_models import SignedWebhookEnvelope


class N8NClient:
    """Small local-first client for outbound workflow triggers."""

    def __init__(
        self,
        outbound_dir: str | Path = "artifacts/workflows/n8n_outbox",
        *,
        settings: Optional[N8NSettings] = None,
    ) -> None:
        self.settings = settings or N8NSettings(outbox_dir=str(outbound_dir))
        self.outbound_dir = Path(self.settings.outbox_dir)

    def trigger_workflow(self, *, workflow_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a signed webhook when configured, otherwise queue locally."""
        target_url = str(self.settings.webhook_url or "").strip()
        signature = self._build_signature(payload)
        if target_url:
            return self._post_signed_webhook(
                workflow_name=workflow_name,
                target_url=target_url,
                payload=payload,
                signature=signature,
            )
        return self._queue_local(
            workflow_name=workflow_name,
            target_url=target_url,
            payload=payload,
            signature=signature,
        )

    def _build_signature(self, payload: Dict[str, Any]) -> Optional[str]:
        secret = os.environ.get(self.settings.shared_secret_env, "")
        if not secret:
            return None
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")
        digest = hmac.new(secret.encode("utf-8"), body, "sha256").hexdigest()
        return f"sha256={digest}"

    def _post_signed_webhook(
        self,
        *,
        workflow_name: str,
        target_url: str,
        payload: Dict[str, Any],
        signature: Optional[str],
    ) -> Dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Haru-Workflow": workflow_name,
        }
        if signature:
            headers["X-Haru-Signature"] = signature
        req = request.Request(target_url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=10) as response:  # nosec B310
            return {
                "status": "sent",
                "workflow_name": workflow_name,
                "target_url": target_url,
                "status_code": response.status,
            }

    def _queue_local(
        self,
        *,
        workflow_name: str,
        target_url: str,
        payload: Dict[str, Any],
        signature: Optional[str],
    ) -> Dict[str, Any]:
        self.outbound_dir.mkdir(parents=True, exist_ok=True)
        path = self.outbound_dir / f"{workflow_name}.json"
        envelope = SignedWebhookEnvelope(
            workflow_name=workflow_name,
            target_url=target_url,
            signature=signature,
            payload=payload,
        )
        path.write_text(envelope.model_dump_json(indent=2), encoding="utf-8")
        return {
            "status": "queued_local",
            "workflow_name": workflow_name,
            "artifact_ref": str(path),
            "signature_attached": signature is not None,
        }
