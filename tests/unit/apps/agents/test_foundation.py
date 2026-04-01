from __future__ import annotations

import json

from apps.agents.core.agent_models import AgentTask, ToolSpec
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import (
    ApprovalMode,
    PermissionTier,
    load_agent_settings,
)
from apps.agents.tools.catalog import build_default_tool_registry
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.core.verifier import AgentVerifier
from apps.agents.integrations.llm_client import NoOpLLMClient
from apps.agents.workflows.noop_workflow import run_noop_workflow


def test_load_agent_settings_from_baseline_config():
    settings = load_agent_settings("config/agent_settings.json")

    assert settings.schema_version == "1.0.0"
    assert settings.default_approval_mode == ApprovalMode.AUTO_READ_ONLY
    assert settings.provider.provider == "noop"
    assert settings.allows_permission(PermissionTier.READ_ONLY)
    assert settings.allows_permission(PermissionTier.ADVISORY_WRITE)
    assert not settings.allows_permission(PermissionTier.PRIVILEGED)


def test_tool_registry_validates_permission_modes():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            tool_name="edge_list_snapshots",
            domain="edge",
            mode=PermissionTier.READ_ONLY,
        ),
        lambda **kwargs: kwargs,
    )

    assert registry.get("edge_list_snapshots") is not None


def test_default_tool_registry_registers_read_only_catalog():
    registry = build_default_tool_registry(
        edge_tools=type(
            "EdgeStub",
            (),
            {
                "edge_list_snapshots": staticmethod(lambda **kwargs: []),
                "edge_get_snapshot": staticmethod(lambda **kwargs: None),
            },
        )(),
        risk_tools=type(
            "RiskStub",
            (),
            {
                "risk_get_snapshot_bundle": staticmethod(lambda **kwargs: {}),
                "risk_get_snapshot_report": staticmethod(lambda **kwargs: {}),
                "replay_get_report": staticmethod(lambda **kwargs: {}),
                "risk_run_what_if": staticmethod(lambda **kwargs: {}),
            },
        )(),
        backtest_tools=type(
            "BacktestStub",
            (),
            {
                "backtest_get_run": staticmethod(lambda **kwargs: {}),
                "backtest_get_trades": staticmethod(lambda **kwargs: []),
                "backtest_get_finance_metrics": staticmethod(lambda **kwargs: {}),
                "optimization_get_run": staticmethod(lambda **kwargs: {}),
                "optimization_get_top_results": staticmethod(lambda **kwargs: []),
                "validation_get_wfo_summary": staticmethod(lambda **kwargs: {}),
                "validation_get_monte_carlo_summary": staticmethod(lambda **kwargs: {}),
                "validation_get_manifest": staticmethod(lambda **kwargs: {}),
            },
        )(),
        report_tools=type(
            "ReportStub",
            (),
            {
                "edge_export_profile_report": staticmethod(lambda **kwargs: {}),
                "risk_export_report": staticmethod(lambda **kwargs: {}),
                "replay_export_report": staticmethod(lambda **kwargs: {}),
                "report_generate_json": staticmethod(lambda **kwargs: {}),
                "report_generate_markdown": staticmethod(lambda **kwargs: {}),
            },
        )(),
        workflow_tools=type(
            "WorkflowStub",
            (),
            {
                "workflow_send_notification": staticmethod(lambda **kwargs: {}),
                "workflow_trigger_n8n": staticmethod(lambda **kwargs: {}),
            },
        )(),
    )

    assert "backtest_get_run" in registry.list_names()
    assert "validation_get_manifest" in registry.list_names()
    assert "workflow_trigger_n8n" in registry.list_names()


def test_noop_workflow_runs_end_to_end_and_writes_audit_log(tmp_path):
    audit_path = tmp_path / "agent_runs.jsonl"
    task = AgentTask(
        task_id="task-001",
        task_type="noop",
        actor_user_id=7,
        actor_role="owner",
        scope="foundation",
        intent="foundation_check",
        input_payload={"message": "phase0"},
        correlation_id="corr-001",
        run_id="run-001",
    )

    result = run_noop_workflow(
        task,
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(audit_path),
        llm_client=NoOpLLMClient(),
    )

    assert result.status == "ok"
    assert "task=task-001" in result.summary
    assert audit_path.exists()

    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["workflow_name"] == "noop_workflow"
    assert entries[0]["status"] == "ok"
