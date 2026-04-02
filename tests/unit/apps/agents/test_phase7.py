from __future__ import annotations

import json

from apps.agents.core.agent_models import AgentTask, ToolSpec
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.reporter import AgentReporter
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.core.policies import load_agent_settings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.live_tools import LiveTools
from apps.agents.tools.report_tools import ReportTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.workflows.daily_desk_pack import run_daily_desk_pack


class _StubEdgeManager:
    def get_profile_snapshots(self, symbol: str, timeframe: str, limit: int = 5):
        return [
            {"snapshot_id": 31, "symbol": symbol, "timeframe": timeframe},
            {"snapshot_id": 30, "symbol": symbol, "timeframe": timeframe},
        ]

    def get_profile_snapshot(self, snapshot_id: int):
        return {
            "snapshot_id": snapshot_id,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "scorecard_summary": {"final_score": 81.0 if snapshot_id == 31 else 77.0, "readiness_label": "ready"},
            "strategy_fit": [{"archetype": "trend_following", "fit_score": 82.0}],
        }


class _StubRiskManager:
    def get_risk_snapshot_bundle(self, snapshot_id: int):
        return {
            "snapshot": {"snapshot_id": snapshot_id, "run_id": 41},
            "recommendations": [{"action_type": "reduce", "symbol": "EURUSD"}],
        }

    def get_risk_run(self, run_id: int):
        return {"run_id": run_id}

    def get_risk_replay_frames(self, run_id: int):
        return [{"frame_id": 1, "run_id": run_id}]


class _StubLiveManager:
    def get_live_session(self, session_id: int):
        return {
            "session_id": session_id,
            "session_name": "Desk",
            "status": "running",
            "total_signals_detected": 8,
            "total_signals_executed": 6,
            "total_signals_rejected": 2,
            "error_message": "",
        }


class _StubReportTools(ReportTools):
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def report_generate_json(self, *, report_name: str, payload):
        path = self.base_dir / f"{report_name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"artifact_type": "json_report", "artifact_ref": str(path)}

    def report_generate_markdown(self, *, report_name: str, content: str):
        path = self.base_dir / f"{report_name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"artifact_type": "markdown_report", "artifact_ref": str(path)}


def _build_strategy_registry():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(tool_name="backtest_get_run", mode="read_only", domain="validation"),
        lambda **kwargs: {"backtest_id": kwargs["backtest_id"]},
    )
    registry.register(
        ToolSpec(tool_name="backtest_get_finance_metrics", mode="read_only", domain="validation"),
        lambda **kwargs: {"summary": {"profit_factor": 1.7, "sharpe_ratio": 1.2, "win_rate": 52.0}},
    )
    registry.register(
        ToolSpec(tool_name="optimization_get_run", mode="read_only", domain="validation"),
        lambda **kwargs: {"status": "completed"},
    )
    registry.register(
        ToolSpec(tool_name="optimization_get_top_results", mode="read_only", domain="validation"),
        lambda **kwargs: [{"backtest_id": 4, "score": 88.0, "rank": 1}],
    )
    registry.register(
        ToolSpec(tool_name="validation_get_wfo_summary", mode="read_only", domain="validation"),
        lambda **kwargs: {"consistency_score": 61.0},
    )
    registry.register(
        ToolSpec(tool_name="validation_get_manifest", mode="read_only", domain="validation"),
        lambda **kwargs: {"strategy_version_id": kwargs["strategy_version_id"]},
    )
    return registry


def test_daily_desk_pack_writes_report_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.agents.tools.risk_tools.build_risk_snapshot_report",
        lambda bundle, run=None: {
            "governance_summary": {"status": "compliant"},
            "portfolio_summary": {"portfolio_var": 1.2},
            "scenarios": [{"loss": -250.0}],
            "recommendations": [{"action_type": "hold"}],
            "snapshot_header": {"run_id": 41},
        },
    )
    monkeypatch.setattr(
        "apps.agents.tools.risk_tools.build_replay_report",
        lambda frames, run=None: {
            "frame_count": len(frames),
            "first_timestamp": "2026-04-01T00:00:00Z",
            "last_timestamp": "2026-04-01T01:00:00Z",
            "summary": {"last_governance_status": "ok", "last_regime_name": "trend", "what_if_available": True},
        },
    )

    result = run_daily_desk_pack(
        AgentTask(
            "desk-pack-1",
            "daily_desk_pack",
            1,
            "owner",
            "desk",
            "daily_desk_pack",
            {
                "symbol": "EURUSD",
                "timeframe": "H1",
                "snapshot_id": 8,
                "session_id": 7,
                "backtest_id": 4,
                "optimization_id": 5,
                "strategy_version_id": 6,
                "incident_run_id": 41,
            },
            "corr-desk",
            "run-desk",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "desk_audit.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        reporter=AgentReporter(_StubReportTools(tmp_path / "reports")),
        tool_registry=_build_strategy_registry(),
        edge_tools=EdgeTools(manager=_StubEdgeManager()),
        risk_tools=RiskTools(manager=_StubRiskManager(), what_if_engine=type("W", (), {})(), what_if_serializer=lambda x: x),
        live_tools=LiveTools(manager=_StubLiveManager(), active_sessions={}),
    )

    assert result.status == "ok"
    assert result.metadata["section_count"] == 5
    assert len(result.metadata["artifact_refs"]) == 2

    report_json = tmp_path / "reports" / "daily_desk_pack_desk-pack-1.json"
    assert report_json.exists()
    packet = json.loads(report_json.read_text(encoding="utf-8"))
    assert packet["title"] == "Daily Desk Pack"
    assert len(packet["sections"]) == 5
