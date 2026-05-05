"""Risk analytics MCP tool adapters over the legacy risk package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from haruquant.utils import logger
from backend_retiring.mcp.mt5_mcp.models import MCPToolSpec


@dataclass(frozen=True)
class RiskAnalyticsTools:
    """MCP-facing adapter for legacy risk analytics helpers."""

    build_snapshot_report: Callable[..., dict[str, Any]]
    evaluate_scenarios: Callable[..., list[Any]]
    build_replay_report: Callable[..., dict[str, Any]]

    def render_snapshot_report(
        self,
        snapshot_bundle: dict[str, Any],
        *,
        run: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = self.build_snapshot_report(snapshot_bundle, run=run)
        return {
            "report_type": "risk_snapshot",
            "snapshot_id": ((report.get("snapshot_header") or {}).get("snapshot_id")),
            "report": report,
        }

    def run_scenario_analysis(self, portfolio_state: Any) -> dict[str, Any]:
        scenarios = self.evaluate_scenarios(portfolio_state)
        normalized = [
            item.to_dict() if hasattr(item, "to_dict") else dict(item)
            for item in scenarios
        ]
        return {
            "scenario_count": len(normalized),
            "scenarios": normalized,
        }

    def render_replay_report(
        self,
        replay_frames: list[dict[str, Any]],
        *,
        run: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = self.build_replay_report(replay_frames, run=run)
        return {
            "report_type": "replay",
            "frame_count": report.get("frame_count", 0),
            "report": report,
        }


RISK_ANALYTICS_TOOL_SPECS: tuple[MCPToolSpec, ...] = (
    MCPToolSpec("render_snapshot_report", "read", "Build a governed report from a legacy risk snapshot bundle."),
    MCPToolSpec("run_scenario_analysis", "read", "Run legacy deterministic scenario analysis."),
    MCPToolSpec("render_replay_report", "read", "Build a governed report from legacy replay frames."),
)


__all__ = [
    "RISK_ANALYTICS_TOOL_SPECS",
    "RiskAnalyticsTools",
]
