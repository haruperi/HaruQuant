from __future__ import annotations

from dataclasses import dataclass

from backend_retiring.mcp.risk_analytics_mcp import (
    RISK_ANALYTICS_TOOL_SPECS,
    RiskAnalyticsMCPServer,
    RiskAnalyticsTools,
    create_risk_analytics_mcp_server,
)


@dataclass(frozen=True)
class FakeScenario:
    name: str
    loss: float

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "loss": self.loss}


def _fake_snapshot_report(snapshot_bundle: dict[str, object], *, run: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "snapshot_header": {"snapshot_id": snapshot_bundle["snapshot_id"]},
        "run": run,
    }


def _fake_scenarios(_: object) -> list[FakeScenario]:
    return [FakeScenario(name="volatility_shock", loss=1250.0)]


def _fake_replay_report(replay_frames: list[dict[str, object]], *, run: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "frame_count": len(replay_frames),
        "run": run,
    }


def test_risk_analytics_mcp_server_starts_with_expected_tool_specs() -> None:
    server = create_risk_analytics_mcp_server()

    assert isinstance(server, RiskAnalyticsMCPServer)
    assert server.name == "risk_analytics_mcp"
    assert server.started is False
    assert server.list_tools() == RISK_ANALYTICS_TOOL_SPECS


def test_risk_analytics_mcp_server_startup_marks_server_ready() -> None:
    server = create_risk_analytics_mcp_server()

    result = server.startup()

    assert result is server
    assert server.started is True


def test_risk_analytics_tools_return_stable_wrapper_shapes() -> None:
    tools = RiskAnalyticsTools(
        build_snapshot_report=_fake_snapshot_report,
        evaluate_scenarios=_fake_scenarios,
        build_replay_report=_fake_replay_report,
    )

    snapshot = tools.render_snapshot_report({"snapshot_id": "snap_001"})
    scenarios = tools.run_scenario_analysis(object())
    replay = tools.render_replay_report([{"frame_timestamp": "2026-04-09T10:00:00Z"}])

    assert snapshot["report_type"] == "risk_snapshot"
    assert snapshot["snapshot_id"] == "snap_001"
    assert scenarios["scenario_count"] == 1
    assert scenarios["scenarios"][0]["name"] == "volatility_shock"
    assert replay["report_type"] == "replay"
    assert replay["frame_count"] == 1
