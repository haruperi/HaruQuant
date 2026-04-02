"""Advisory workflow notification and outbound trigger helpers."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from apps.agents.core.agent_models import ApprovalDecision
from apps.agents.core.approvals import (
    ApprovalActionType,
    ApprovalStore,
    append_approval_audit_event,
    build_target_ref,
)
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.policies import (
    ApprovalMode,
    AgentSettings,
    PermissionTier,
    load_agent_settings,
)
from apps.agents.integrations.n8n_client import N8NClient
from apps.api.routes import live as live_routes
from apps.live.config import Config as LiveConfig
from apps.notifications.base import NotificationLevel, NotificationMessage
from apps.notifications.manager import NotificationManager


class WorkflowTools:
    """Send notifications or enqueue outbound workflow payloads safely."""

    def __init__(
        self,
        *,
        notification_manager: Optional[NotificationManager] = None,
        n8n_client: Optional[N8NClient] = None,
        approval_store: Optional[ApprovalStore] = None,
        audit_logger: Optional[AgentAuditLogger] = None,
        settings: Optional[AgentSettings] = None,
        live_pause_handler: Any = None,
        live_stop_handler: Any = None,
        live_deploy_handler: Any = None,
        live_config_manager: Optional[LiveConfig] = None,
    ) -> None:
        self.settings = settings or load_agent_settings("config/agent_settings.json")
        self.notification_manager = notification_manager or NotificationManager()
        self.n8n_client = n8n_client or N8NClient()
        self.approval_store = approval_store or ApprovalStore(self.settings.approvals.store_dir)
        self.audit_logger = audit_logger or AgentAuditLogger(self.settings.audit_log_path)
        self.live_pause_handler = live_pause_handler or self._pause_live_session
        self.live_stop_handler = live_stop_handler or self._stop_live_session
        self.live_deploy_handler = live_deploy_handler or self._advisory_live_deploy
        self.live_config_manager = live_config_manager or LiveConfig(
            str(Path("config") / "live_trading_config.toml"),
            profile="live",
        )

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

    def approval_request_action(
        self,
        *,
        action_type: str,
        requested_by_user_id: int,
        requested_by_role: str,
        rationale: str,
        request_payload: Dict[str, Any],
        approval_mode: str = ApprovalMode.REQUIRE_APPROVAL,
    ) -> Dict[str, Any]:
        """Create one approval artifact for a privileged action."""
        self._ensure_privileged_allowed()
        normalized_mode = str(approval_mode).strip().lower()
        if normalized_mode == ApprovalMode.DENY_PRIVILEGED:
            raise ValueError("Privileged approvals are denied for the current task.")
        approval = self.approval_store.create_request(
            action_type=action_type,
            requested_by_user_id=requested_by_user_id,
            requested_by_role=requested_by_role,
            rationale=rationale,
            request_payload=request_payload,
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=approval,
            event_type="approval_requested",
            actor_user_id=requested_by_user_id,
            actor_role=requested_by_role,
            status=approval.status,
            metadata={"target_ref": approval.target_ref},
        )
        return approval.to_dict()

    def approval_get_status(self, *, approval_id: str) -> Dict[str, Any]:
        """Return one persisted approval artifact."""
        return self.approval_store.get_request(approval_id).to_dict()

    def approval_apply_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        actor_user_id: int,
        actor_role: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Apply one human approval decision."""
        self._ensure_privileged_allowed()
        updated = self.approval_store.apply_decision(
            ApprovalDecision(
                approval_id=approval_id,
                decision=decision,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                notes=notes,
            )
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=updated,
            event_type="approval_decided",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            status=updated.status,
            metadata={"decision": updated.decision},
        )
        return updated.to_dict()

    def privileged_strategy_promote(
        self,
        *,
        approval_id: str,
        strategy_version_id: int,
        summary: str = "",
    ) -> Dict[str, Any]:
        """Mark one strategy promotion as approved and applied without mutating strategy state."""
        self._ensure_privileged_allowed()
        payload = {"strategy_version_id": int(strategy_version_id)}
        approval = self._require_approved_action(
            approval_id=approval_id,
            action_type=ApprovalActionType.STRATEGY_PROMOTION,
            request_payload=payload,
        )
        applied = self.approval_store.mark_applied(
            approval_id=approval_id,
            execution_metadata={
                "status": "advisory_only",
                "strategy_version_id": int(strategy_version_id),
                "summary": str(summary).strip(),
            },
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=applied,
            event_type="approval_executed",
            actor_user_id=approval.requested_by_user_id,
            actor_role=approval.requested_by_role,
            status=applied.status,
            metadata={"execution_type": "strategy_promotion_advisory"},
        )
        return {
            "status": "applied",
            "mode": "advisory_only",
            "approval_id": approval_id,
            "strategy_version_id": int(strategy_version_id),
        }

    def privileged_live_deploy(
        self,
        *,
        approval_id: str,
        session_id: int,
    ) -> Dict[str, Any]:
        """Apply one approval-gated live deployment handoff."""
        self._ensure_privileged_allowed()
        approval = self._require_approved_action(
            approval_id=approval_id,
            action_type=ApprovalActionType.LIVE_DEPLOYMENT,
            request_payload={"session_id": int(session_id)},
        )
        result = dict(self.live_deploy_handler(session_id=int(session_id)))
        applied = self.approval_store.mark_applied(
            approval_id=approval_id,
            execution_metadata=result,
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=applied,
            event_type="approval_executed",
            actor_user_id=approval.requested_by_user_id,
            actor_role=approval.requested_by_role,
            status=applied.status,
            metadata={"execution_type": "live_deployment"},
        )
        return result

    def privileged_live_pause_session(
        self,
        *,
        approval_id: str,
        session_id: int,
        authorization_token: str,
    ) -> Dict[str, Any]:
        """Pause one live session only when approval exists and matches the target."""
        self._ensure_privileged_allowed()
        approval = self._require_approved_action(
            approval_id=approval_id,
            action_type=ApprovalActionType.LIVE_PAUSE_SESSION,
            request_payload={"session_id": int(session_id)},
        )
        result = dict(
            self.live_pause_handler(
                session_id=int(session_id),
                authorization_token=authorization_token,
            )
        )
        applied = self.approval_store.mark_applied(
            approval_id=approval_id,
            execution_metadata=result,
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=applied,
            event_type="approval_executed",
            actor_user_id=approval.requested_by_user_id,
            actor_role=approval.requested_by_role,
            status=applied.status,
            metadata={"execution_type": "live_pause_session"},
        )
        return result

    def privileged_live_stop_session(
        self,
        *,
        approval_id: str,
        session_id: int,
        authorization_token: str,
    ) -> Dict[str, Any]:
        """Stop one live session only when approval exists and matches the target."""
        self._ensure_privileged_allowed()
        approval = self._require_approved_action(
            approval_id=approval_id,
            action_type=ApprovalActionType.LIVE_STOP_SESSION,
            request_payload={"session_id": int(session_id)},
        )
        result = dict(
            self.live_stop_handler(
                session_id=int(session_id),
                authorization_token=authorization_token,
            )
        )
        applied = self.approval_store.mark_applied(
            approval_id=approval_id,
            execution_metadata=result,
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=applied,
            event_type="approval_executed",
            actor_user_id=approval.requested_by_user_id,
            actor_role=approval.requested_by_role,
            status=applied.status,
            metadata={"execution_type": "live_stop_session"},
        )
        return result

    def privileged_risk_override(
        self,
        *,
        approval_id: str,
        key: str,
        value: Any,
        authorization_token: str,
        reason: str,
        actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply one live risk override only when approval exists and matches the target."""
        self._ensure_privileged_allowed()
        approval = self._require_approved_action(
            approval_id=approval_id,
            action_type=ApprovalActionType.RISK_OVERRIDE,
            request_payload={"key": key},
        )
        self.live_config_manager.apply_risk_override(
            key=key,
            value=value,
            authorization_token=authorization_token,
            reason=reason,
            actor=actor,
        )
        result = {
            "status": "applied",
            "approval_id": approval_id,
            "key": str(key).strip(),
            "value": value,
        }
        applied = self.approval_store.mark_applied(
            approval_id=approval_id,
            execution_metadata=result,
        )
        append_approval_audit_event(
            self.audit_logger,
            approval=applied,
            event_type="approval_executed",
            actor_user_id=approval.requested_by_user_id,
            actor_role=approval.requested_by_role,
            status=applied.status,
            metadata={"execution_type": "risk_override"},
        )
        return result

    def _require_approved_action(
        self,
        *,
        approval_id: str,
        action_type: str,
        request_payload: Dict[str, Any],
    ):
        target_ref = build_target_ref(action_type, request_payload)
        return self.approval_store.require_approved_request(
            approval_id=approval_id,
            action_type=action_type,
            target_ref=target_ref,
        )

    def _ensure_privileged_allowed(self) -> None:
        if not self.settings.allows_permission(PermissionTier.PRIVILEGED):
            raise ValueError("Privileged agent actions are disabled by current settings.")

    def _pause_live_session(self, *, session_id: int, authorization_token: str) -> Dict[str, Any]:
        return self._run_async_handler(
            live_routes.pause_session(session_id=int(session_id), authorization=authorization_token)
        )

    def _stop_live_session(self, *, session_id: int, authorization_token: str) -> Dict[str, Any]:
        return self._run_async_handler(
            live_routes.stop_session(session_id=int(session_id), authorization=authorization_token)
        )

    def _advisory_live_deploy(self, *, session_id: int) -> Dict[str, Any]:
        return {
            "status": "applied",
            "mode": "advisory_only",
            "session_id": int(session_id),
        }

    def _run_async_handler(self, coroutine: Any) -> Dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return dict(asyncio.run(coroutine))
        raise RuntimeError("Privileged live session control tools must run from a synchronous context.")
