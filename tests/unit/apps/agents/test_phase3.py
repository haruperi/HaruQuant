from __future__ import annotations

import json

from apps.agents.tools.catalog import build_default_tool_registry
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.tools.workflow_tools import WorkflowTools
from apps.agents.integrations.n8n_client import N8NClient


class _StubWhatIfEngine:
    def evaluate(self, frame, actions, include_recommendations=True):
        return {
            "frame": frame,
            "actions_count": len(actions),
            "include_recommendations": include_recommendations,
        }


def test_risk_run_what_if_uses_safe_serializer():
    tools = RiskTools(
        manager=type("RiskMgr", (), {})(),
        what_if_engine=_StubWhatIfEngine(),
        what_if_serializer=lambda comparison: {
            "ok": True,
            "actions_count": comparison["actions_count"],
            "include_recommendations": comparison["include_recommendations"],
        },
    )

    result = tools.risk_run_what_if(
        frame=object(),
        actions=[
            {"action_type": "reduce", "symbol": "EURUSD", "delta_lots": 0.1},
            {"action_type": "add", "symbol": "GBPUSD", "delta_lots": 0.2},
        ],
    )

    assert result["ok"] is True
    assert result["actions_count"] == 2


def test_workflow_trigger_n8n_writes_local_outbox(tmp_path):
    client = N8NClient(outbound_dir=tmp_path)
    tools = WorkflowTools(
        notification_manager=type(
            "NotifMgr",
            (),
            {"notifiers": {}, "send_notification": staticmethod(lambda *args, **kwargs: {})},
        )(),
        n8n_client=client,
    )

    result = tools.workflow_trigger_n8n(
        workflow_name="daily_brief",
        payload={"summary": "ok"},
    )

    assert result["status"] == "queued_local"
    stored = json.loads((tmp_path / "daily_brief.json").read_text(encoding="utf-8"))
    assert stored["summary"] == "ok"


def test_default_tool_registry_includes_phase3_advisory_tools():
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

    assert "risk_run_what_if" in registry.list_names()
    assert "report_generate_markdown" in registry.list_names()
    assert "workflow_send_notification" in registry.list_names()
