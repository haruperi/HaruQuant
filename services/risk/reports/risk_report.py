"""Public risk report builder facade."""

from __future__ import annotations

from typing import Any

from .risk_report_builder import build_risk_snapshot_report


class RiskReportBuilder:
    """Build machine-readable risk reports from current snapshot bundles."""

    def build_current_report(self, state: dict[str, Any]) -> dict[str, Any]:
        return build_risk_snapshot_report(state)


__all__ = ["RiskReportBuilder"]
