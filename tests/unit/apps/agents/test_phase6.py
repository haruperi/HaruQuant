from __future__ import annotations

import json

import pytest

from apps.agents.tools.workflow_tools import WorkflowTools


class _StubRiskConfigManager:
    def __init__(self) -> None:
        self.calls = []

    def apply_risk_override(
        self,
        key,
        value,
        *,
        authorization_token,
        reason,
        actor=None,
        audit_log_path=None,
    ) -> None:
        self.calls.append(
            {
                "key": key,
                "value": value,
                "authorization_token": authorization_token,
                "reason": reason,
                "actor": actor,
            }
        )


def _build_tools(tmp_path, *, pause_handler=None, stop_handler=None, deploy_handler=None):
    return WorkflowTools(
        approval_store=None,
        audit_logger=None,
        settings=type(
            "Settings",
            (),
            {
                "approvals": type("Approvals", (), {"store_dir": str(tmp_path / "approvals")})(),
                "audit_log_path": str(tmp_path / "agent_audit.jsonl"),
                "allows_permission": staticmethod(lambda tier: True),
            },
        )(),
        notification_manager=type(
            "NotifMgr",
            (),
            {"notifiers": {}, "send_notification": staticmethod(lambda *args, **kwargs: {})},
        )(),
        n8n_client=type("N8N", (), {"trigger_workflow": staticmethod(lambda **kwargs: kwargs)})(),
        live_pause_handler=pause_handler or (lambda **kwargs: {"status": "paused", **kwargs}),
        live_stop_handler=stop_handler or (lambda **kwargs: {"status": "stopped", **kwargs}),
        live_deploy_handler=deploy_handler or (lambda **kwargs: {"status": "applied", **kwargs}),
        live_config_manager=_StubRiskConfigManager(),
    )


def test_approval_request_and_decision_lifecycle(tmp_path):
    tools = _build_tools(tmp_path)

    created = tools.approval_request_action(
        action_type="live_stop_session",
        requested_by_user_id=11,
        requested_by_role="ops",
        rationale="Emergency halt",
        request_payload={"session_id": 42, "correlation_id": "corr-42", "run_id": "run-42"},
    )
    assert created["status"] == "pending"
    assert created["target_ref"] == "live_session:42"

    decided = tools.approval_apply_decision(
        approval_id=created["approval_id"],
        decision="approve",
        actor_user_id=7,
        actor_role="owner",
        notes="Approved",
    )
    assert decided["status"] == "approved"

    status = tools.approval_get_status(approval_id=created["approval_id"])
    assert status["decision"] == "approve"


def test_privileged_live_stop_requires_matching_approval(tmp_path):
    tools = _build_tools(tmp_path)
    created = tools.approval_request_action(
        action_type="live_stop_session",
        requested_by_user_id=11,
        requested_by_role="ops",
        rationale="Stop live session",
        request_payload={"session_id": 42},
    )
    tools.approval_apply_decision(
        approval_id=created["approval_id"],
        decision="approve",
        actor_user_id=7,
        actor_role="owner",
    )

    result = tools.privileged_live_stop_session(
        approval_id=created["approval_id"],
        session_id=42,
        authorization_token="token",
    )
    assert result["status"] == "stopped"

    with pytest.raises(ValueError):
        tools.privileged_live_stop_session(
            approval_id=created["approval_id"],
            session_id=99,
            authorization_token="token",
        )


def test_privileged_risk_override_marks_request_applied(tmp_path):
    risk_manager = _StubRiskConfigManager()
    tools = WorkflowTools(
        settings=type(
            "Settings",
            (),
            {
                "approvals": type("Approvals", (), {"store_dir": str(tmp_path / "approvals")})(),
                "audit_log_path": str(tmp_path / "agent_audit.jsonl"),
                "allows_permission": staticmethod(lambda tier: True),
            },
        )(),
        notification_manager=type(
            "NotifMgr",
            (),
            {"notifiers": {}, "send_notification": staticmethod(lambda *args, **kwargs: {})},
        )(),
        n8n_client=type("N8N", (), {"trigger_workflow": staticmethod(lambda **kwargs: kwargs)})(),
        live_pause_handler=lambda **kwargs: kwargs,
        live_stop_handler=lambda **kwargs: kwargs,
        live_deploy_handler=lambda **kwargs: kwargs,
        live_config_manager=risk_manager,
    )

    created = tools.approval_request_action(
        action_type="risk_override",
        requested_by_user_id=2,
        requested_by_role="risk",
        rationale="Temporarily widen limit",
        request_payload={"key": "safety.max_positions"},
    )
    tools.approval_apply_decision(
        approval_id=created["approval_id"],
        decision="approve",
        actor_user_id=1,
        actor_role="owner",
    )

    result = tools.privileged_risk_override(
        approval_id=created["approval_id"],
        key="safety.max_positions",
        value=12,
        authorization_token="signed-token",
        reason="Desk override",
        actor="risk-lead",
    )

    assert result["status"] == "applied"
    assert risk_manager.calls[0]["key"] == "safety.max_positions"

    status = tools.approval_get_status(approval_id=created["approval_id"])
    assert status["status"] == "applied"

    audit_entries = [
        json.loads(line)
        for line in (tmp_path / "agent_audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert audit_entries[-1]["event_type"] == "approval_executed"
